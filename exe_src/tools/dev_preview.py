"""开发用预览工具：渲染各界面为 PNG，方便在无显示器的环境里检查排版。

用法：
    python tools/dev_preview.py [输出目录]

可选环境变量：
    GIDMG_DEV_FONT   额外注册的字体文件（例如思源黑体），用于渲染中文。
    GIDMG_DATA_DIR   数据目录，默认用临时目录，避免污染真实配置。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("GIDMG_DATA_DIR", tempfile.mkdtemp(prefix="gidmg-preview-"))

from PySide6.QtCore import QCoreApplication, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gidmg.core import state as st  # noqa: E402
from gidmg.ui import theme  # noqa: E402

# 截图时关闭入场/过渡动画，确保抓到的是终态而不是动画中间帧。
theme.ANIMATIONS = False


def _register_dev_font() -> None:
    path = os.environ.get("GIDMG_DEV_FONT")
    if not path or not Path(path).exists():
        return
    fid = QFontDatabase.addApplicationFont(path)
    families = QFontDatabase.applicationFontFamilies(fid)
    if families:
        theme._UI_FAMILIES.insert(0, families[0])


def _demo_state() -> dict:
    s = st.def_state()
    s["timelineEnabled"] = True
    s["dmgShareEnabled"] = True
    s["rotationDuration"] = 21
    s["enemy"] = {"level": 103, "res": {"pyro": 10, "hydro": 10, "electro": 10, "cryo": 10,
                                        "dendro": 10, "anemo": 10, "geo": 10, "physical": 30}}

    hutao = st.def_char("pyro")
    hutao.update(name="胡桃", lv=90, hpFlat=15552, atkFlat=1200, critRate=66.2,
                 critDMG=189.5, em=140)
    d1 = st.new_dmg_source("normal")
    d1.update(name="重击·蒸发", stat="atk", mult=242.6, element="pyro", dmgType="CA",
              reaction="vape", triggerCharId=hutao["id"], statCharId=hutao["id"],
              timingMode="uniform_dynamic", startTime=3, duration=7)
    hutao["dmgSrcs"] = [d1]
    t1 = st.new_talent("蝶隐之时")
    t1["effs"][0].update(cat="stat", type="atk_flat", value=976, target="self")
    t1.update(startTime=0, duration=9, isPermanent=False)
    hutao["talents"] = [t1]

    yelan = st.def_char("hydro")
    yelan.update(name="夜兰", lv=90, hpFlat=30130, atkFlat=850, critRate=62.5, critDMG=155.4)
    d2 = st.new_dmg_source("normal")
    d2.update(name="破局矢", stat="hp", mult=13.5, element="hydro", dmgType="Q",
              reaction="none", triggerCharId=yelan["id"], statCharId=yelan["id"],
              timingMode="uniform_snapshot", startTime=1, duration=15)
    yelan["dmgSrcs"] = [d2]
    t2 = st.new_talent("猜先有方")
    t2["effs"][0].update(cat="dmgType", type="all", value=35, target="team")
    t2.update(startTime=1, duration=15, isPermanent=False)
    yelan["talents"] = [t2]

    xingqiu = st.def_char("hydro")
    xingqiu.update(name="行秋", lv=90, hpFlat=13348, atkFlat=920, critRate=55.1, critDMG=142.8)
    d3 = st.new_dmg_source("trans")
    d3.update(name="感电", transType="electrocharged", triggerCharId=xingqiu["id"],
              statCharId=xingqiu["id"], triggerCount=6, timingMode="instant", startTime=6)
    xingqiu["dmgSrcs"] = [d3]

    zhongli = st.def_char("geo")
    zhongli.update(name="钟离", lv=90, hpFlat=40000, atkFlat=740, critRate=5, critDMG=50, on=False)

    s["chars"] = [hutao, yelan, xingqiu, zhongli]
    s["selId"] = hutao["id"]
    return s


def grab(widget: QWidget, path: Path, size=None) -> None:
    if size:
        widget.resize(*size)
    widget.show()
    QApplication.processEvents()
    for _ in range(3):
        QApplication.processEvents()
    widget.grab().save(str(path))
    print(f"  · {path.name}  ({widget.width()}×{widget.height()})")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "docs" / "preview")
    out.mkdir(parents=True, exist_ok=True)

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    _register_dev_font()
    app.setFont(theme.ui_font(9.5))
    app.setStyleSheet(theme.stylesheet())

    from gidmg.ui.app import MainWindow
    from gidmg.ui.dialogs import (detail, dmgshare, formula, history, quickset, quicktable,
                                  settings, skill_inspect)

    win = MainWindow()
    win.resize(1440, 900)

    print("渲染中……")
    grab(win, out / "01-launcher.png")

    win.create_config("示例配置", _demo_state())
    s = win.session
    s.recalc()
    QApplication.processEvents()

    win.editor.set_workspace("character")
    grab(win, out / "02-editor-character.png")
    win.editor.set_workspace("monster")
    grab(win, out / "03-editor-monster.png")
    win.editor.set_workspace("timeline")
    grab(win, out / "04-editor-timeline.png")
    win.editor.set_workspace("character")

    win.island.peek(True, animate=False)
    grab(win, out / "05-island-peek.png")
    win.island.expand(animate=False)
    grab(win, out / "06-island-expanded.png")
    win.island.collapse(animate=False)

    for name, dlg in (("07-dialog-settings", settings.SettingsDialog(win, s)),
                      ("08-dialog-quickset", quickset.QuickSetterDialog(win, s)),
                      ("09-dialog-detail", detail.DetailDialog(win, s)),
                      ("10-dialog-dmgshare", dmgshare.DmgShareDialog(win, s)),
                      ("11-dialog-formula", formula.FormulaDialog(win)),
                      ("12-dialog-history", history.HistoryDialog(win, s)),
                      ("13-dialog-quicktable", quicktable.SchemeCollector(win, s, win.editor))):
        grab(dlg, out / f"{name}.png")
        dlg.close()

    sid = next(iter(s.result.get("inspectMap") or {}), None)
    if sid:
        dlg = skill_inspect.SkillInspectDialog(win, s, sid)
        grab(dlg, out / "14-dialog-skill-inspect.png")
        dlg.close()

    # 存两份配置，回到配置管理页展示列表形态
    s.save()
    s.capture_history()
    win.create_config("纳西妲·超绽放", _demo_state())
    win.session.save()
    win.back_to_launcher()
    QApplication.processEvents()
    grab(win, out / "15-launcher-with-configs.png")

    print(f"完成，输出目录：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
