"""界面冒烟测试：离屏把主窗口和所有弹窗都构造一遍。

作用是挡住「改了 core 的函数名，UI 里忘了同步」这类回归。
没有可用的 Qt 平台插件时（例如缺少图形库的精简容器）整组测试会跳过。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # 缺少图形库时（例如精简容器）整组跳过，而不是让收集阶段报错
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover - 取决于运行环境
    pytest.skip(f"Qt 不可用，跳过界面冒烟测试：{exc}", allow_module_level=True)


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    existing = QApplication.instance()
    if existing is not None:
        yield existing
        return
    try:
        instance = QApplication([])
    except Exception as exc:  # 平台插件不可用
        pytest.skip(f"无法创建 QApplication：{exc}")
    from gidmg.ui import theme
    instance.setFont(theme.ui_font(9.5))
    instance.setStyleSheet(theme.stylesheet())
    yield instance


def _silence_modals(monkeypatch, role=None):
    """把所有模态框改成不阻塞，并固定选中某个按钮角色。

    默认选「破坏性」按钮（不保存退出 / 放弃修改 / 打开已保存版本），
    这样测试里关窗、放弃修改都不会卡在事件循环里。
    """
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    role = role or QMessageBox.ButtonRole.DestructiveRole

    def fake_exec(self):
        picked = None
        for btn in self.buttons():
            if self.buttonRole(btn) == role:
                picked = btn
                break
        self._auto_picked = picked
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec, raising=False)
    monkeypatch.setattr(QMessageBox, "clickedButton",
                        lambda self: getattr(self, "_auto_picked", None), raising=False)
    for name, answer in (("warning", QMessageBox.StandardButton.Ok),
                         ("information", QMessageBox.StandardButton.Ok),
                         ("critical", QMessageBox.StandardButton.Ok),
                         ("question", QMessageBox.StandardButton.Yes)):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda *a, _r=answer, **kw: _r), raising=False)
    monkeypatch.setattr(QInputDialog, "getText",
                        staticmethod(lambda *a, **kw: ("", False)), raising=False)


@pytest.fixture()
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv("GIDMG_DATA_DIR", str(tmp_path / "date"))
    _silence_modals(monkeypatch)
    from gidmg.core.storage import Storage
    from gidmg.ui.app import MainWindow
    win = MainWindow(Storage(tmp_path / "date"))
    yield win
    win.close()


def _demo(win):
    """建一个带三类伤害来源的配置，保证各面板都有内容可渲染。"""
    from gidmg.core import state as st

    win.create_config("冒烟配置", st.def_state())
    s = win.session
    a = s.add_char()
    a.update(name="甲", element="pyro", atkFlat=1500, critRate=60, critDMG=150, em=200)
    b = s.add_char()
    b.update(name="乙", element="electro", atkFlat=1200, critRate=50, critDMG=120)

    d1 = st.new_dmg_source("normal")
    d1.update(name="重击", stat="atk", mult=250, element="pyro", dmgType="CA", reaction="vape",
              triggerCharId=a["id"], statCharId=a["id"],
              timingMode="uniform_dynamic", startTime=2, duration=6)
    a["dmgSrcs"] = [d1]

    d2 = st.new_dmg_source("trans")
    d2.update(name="超载", transType="overloaded", triggerCharId=b["id"], statCharId=b["id"],
              triggerCount=3, timingMode="instant", startTime=5)
    b["dmgSrcs"] = [d2]

    t = st.new_talent("测试天赋")
    t["effs"][0].update(cat="stat", type="atk_pct", value=25, target="team")
    b["talents"] = [t]

    s.state["timelineEnabled"] = True
    s.state["dmgShareEnabled"] = True
    s.touch(chars=True, editor=True, immediate=True)
    return s


def test_main_window_and_workspaces(window):
    s = _demo(window)
    assert s.result["total"] > 0
    assert len(s.result["results"]) == 2

    for key in ("character", "monster", "timeline", "不存在的键"):
        window.editor.set_workspace(key)
    window.editor.refresh_sidebar()
    window.editor.set_quick_table_mode(True)
    window.editor.set_quick_table_mode(False)

    window.island.set_config_name("冒烟配置")
    window.island.expand(animate=False)
    window.island.collapse(animate=False)


def test_all_dialogs_construct(window):
    s = _demo(window)
    from gidmg.ui.dialogs import (detail, dmgshare, formula, history, quickset, quicktable,
                                  settings, skill_inspect)

    dialogs = [
        settings.SettingsDialog(window, s),
        history.HistoryDialog(window, s),
        quickset.QuickSetterDialog(window, s),
        quickset.LibraryDialog(window, s, "weapon"),
        quickset.LibraryDialog(window, s, "artifact"),
        quicktable.SchemeCollector(window, s, window.editor),
        quicktable.ProgressDialog(window, 10),
        detail.DetailDialog(window, s),
        dmgshare.DmgShareDialog(window, s),
        formula.FormulaDialog(window),
    ]
    source_id = next(iter(s.result.get("inspectMap") or {}), None)
    assert source_id, "应当有可解析的伤害来源"
    dialogs.append(skill_inspect.SkillInspectDialog(window, s, source_id))

    s.add_baseline("基准")
    dialogs.append(detail.BaselineSnapshotDialog(window, s, s.baselines[0]["id"]))

    for dlg in dialogs:
        assert dlg.windowTitle()
        dlg.close()


def test_quick_table_results_dialog(window):
    import copy
    from gidmg.core import quicktable as qtc
    from gidmg.ui.dialogs import quicktable

    s = _demo(window)
    first = s.chars[0]
    schemes = {first["id"]: [qtc.Scheme(first["id"], "方案A", 1.0, copy.deepcopy(first)),
                             qtc.Scheme(first["id"], "方案B", 2.0, copy.deepcopy(first))]}
    rows = qtc.run(s.state, schemes, None)
    assert len(rows) == 2

    info = [{"id": c["id"], "name": c["name"]} for c in s.enabled_chars]
    dlg = quicktable.ResultsDialog(window, s, rows, info)
    assert dlg.table.rowCount() == 2
    assert dlg.table.columnCount() >= 3
    dlg._sort_dmg()
    dlg._toggle_prune()
    dlg.close()


def test_save_and_reopen_round_trip(window):
    s = _demo(window)
    total = s.result["total"]
    window.save_and_exit()
    assert not s.dirty

    names = [m.name for m in window.storage.list_configs()]
    assert "冒烟配置" in names

    window.open_config("冒烟配置")
    assert window.session.config_name == "冒烟配置"
    assert window.session.result["total"] == pytest.approx(total)
    assert len(window.session.chars) == 2


def test_discard_exit_keeps_saved_copy(window):
    s = _demo(window)
    window.save_and_exit()
    window.open_config("冒烟配置")
    s = window.session
    s.chars[0]["name"] = "改过的名字"
    s.touch(chars=True, immediate=True)
    assert s.dirty
    window.discard_and_exit()

    window.open_config("冒烟配置")
    assert window.session.chars[0]["name"] == "甲"
