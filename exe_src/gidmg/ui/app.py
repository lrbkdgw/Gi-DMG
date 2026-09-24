"""应用外壳：配置管理页 ↔ 编辑页 的切换与全局快捷键。"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QInputDialog, QMainWindow, QMessageBox,
                               QStackedWidget, QWidget)

from ..core.constants import APP_TITLE
from ..core.storage import Storage
from ..version import VERSION
from . import icons, theme
from .editor import EditorView
from .island import IslandHost
from .launcher import LauncherView
from .session import Session


class MainWindow(QMainWindow):
    def __init__(self, storage: Optional[Storage] = None):
        super().__init__()
        self.storage = storage or Storage()
        self.storage.ensure()
        self.settings = self.storage.load_settings()
        self.session = Session(self.storage, self)

        self.setWindowTitle(f"{APP_TITLE} v{VERSION}")
        self.setWindowIcon(icons.app_icon())
        self.resize(1440, 900)
        self.setMinimumSize(1120, 700)
        self._restore_geometry()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ---- 配置管理页
        self.launcher = LauncherView(self.storage)
        self.launcher.openConfig.connect(self.open_config)
        self.launcher.createConfig.connect(self.create_config)
        self.launcher.showFormula.connect(self.show_formula)
        self.stack.addWidget(self.launcher)

        # ---- 编辑页（含灵动岛）
        self.editor = EditorView(self.session)
        self.editor_host = IslandHost(self.editor)
        self.island = self.editor_host.island
        self.island.saveExit.connect(self.save_and_exit)
        self.island.discardExit.connect(self.discard_and_exit)
        self.island.quickTable.connect(self.open_quick_table)
        self.island.settings.connect(self.open_settings)
        self.island.renameRequested.connect(self.rename_config)
        self.stack.addWidget(self.editor_host)

        self.session.nameChanged.connect(self.island.set_config_name)
        self.session.dirtyChanged.connect(self.island.set_dirty)

        self._wire_dialogs()
        self._wire_shortcuts()
        self.stack.setCurrentWidget(self.launcher)

    # ------------------------------------------------------------------ 弹窗

    def _wire_dialogs(self) -> None:
        from .dialogs import (detail, dmgshare, formula, history, quicktable,
                              settings as settings_dlg, skill_inspect, quickset)

        self._dlg = {
            "detail": detail, "dmgshare": dmgshare, "formula": formula,
            "history": history, "quicktable": quicktable, "settings": settings_dlg,
            "skill_inspect": skill_inspect, "quickset": quickset,
        }
        self.editor.openHistory.connect(self.open_history)
        self.editor.openSettings.connect(self.open_settings)
        self.editor.openQuickSetter.connect(self.open_quick_setter)
        self.editor.openDetails.connect(self.open_details)
        self.editor.openDmgShare.connect(self.open_dmg_share)
        self.editor.inspectSource.connect(self.open_skill_inspect)
        self.editor.viewBaseline.connect(self.view_baseline)
        self.editor.restoreBaseline.connect(self.restore_baseline)

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Save, self, self._quick_save)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.open_quick_table)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)

    # ------------------------------------------------------------------ 导航

    def open_config(self, name: str) -> None:
        draft = self.storage.load_draft(name)
        state = None
        if draft is not None:
            box = QMessageBox(self)
            box.setWindowTitle("发现未保存的修改")
            box.setText(f"配置「{name}」上次退出时留有未保存的草稿。")
            box.setInformativeText("要恢复草稿内容，还是打开上次已保存的版本？")
            restore = box.addButton("恢复草稿", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("打开已保存版本", QMessageBox.ButtonRole.DestructiveRole)
            box.exec()
            if box.clickedButton() is restore:
                state = draft
            else:
                self.storage.clear_draft(name)
        try:
            self.session.open(name, state)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "打开失败", f"无法读取该配置：\n{exc}")
            return
        if state is not None:
            self.session.set_dirty(True)
        self.editor.set_workspace("character")
        self.editor.refresh_sidebar()
        self.stack.setCurrentWidget(self.editor_host)
        self.island.set_config_name(self.session.config_name)
        self.island.set_dirty(self.session.dirty)

    def create_config(self, name: str, state: dict) -> None:
        real = self.storage.create_config(name, state)
        self.open_config(real)

    def back_to_launcher(self) -> None:
        self.session.close()
        self.launcher.reload()
        self.stack.setCurrentWidget(self.launcher)

    def save_and_exit(self) -> None:
        self.session.save()
        self.session.capture_history()
        self.back_to_launcher()

    def discard_and_exit(self) -> None:
        if self.session.dirty:
            box = QMessageBox(self)
            box.setWindowTitle("不保存并退出")
            box.setText("当前配置有未保存的修改。")
            box.setInformativeText("退出后这些修改会丢失，确定吗？")
            box.setIcon(QMessageBox.Icon.Warning)
            drop = box.addButton("放弃修改并退出", QMessageBox.ButtonRole.DestructiveRole)
            box.addButton("返回继续编辑", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not drop:
                return
        self.session.discard()
        self.back_to_launcher()

    def rename_config(self) -> None:
        new, ok = QInputDialog.getText(self, "重命名配置", "新的名称：",
                                       text=self.session.config_name)
        if ok and new.strip():
            self.session.rename(new.strip())

    def _quick_save(self) -> None:
        if self.stack.currentWidget() is self.editor_host:
            self.session.save()

    def _on_escape(self) -> None:
        if self.stack.currentWidget() is self.editor_host:
            self.island.set_actions_visible(False)

    # ------------------------------------------------------------------ 弹窗入口

    def open_settings(self) -> None:
        self._dlg["settings"].open_settings(self, self.session)

    def open_history(self) -> None:
        self._dlg["history"].open_history(self, self.session)

    def open_quick_table(self) -> None:
        self._dlg["quicktable"].open_quick_table(self, self.session, self.editor)

    def open_quick_setter(self) -> None:
        self._dlg["quickset"].open_quick_setter(self, self.session)

    def open_details(self) -> None:
        self._dlg["detail"].open_details(self, self.session)

    def open_dmg_share(self) -> None:
        self._dlg["dmgshare"].open_dmg_share(self, self.session)

    def open_skill_inspect(self, source_id: str) -> None:
        self._dlg["skill_inspect"].open_skill_inspect(self, self.session, source_id)

    def show_formula(self) -> None:
        self._dlg["formula"].open_formula(self)

    def view_baseline(self, bid: str) -> None:
        self._dlg["detail"].open_baseline_snapshot(self, self.session, bid)

    def restore_baseline(self, bid: str) -> None:
        b = next((x for x in self.session.baselines if x.get("id") == bid), None)
        if not b or not b.get("config"):
            return
        if QMessageBox.question(self, "设为当前配置",
                                f"用基准「{b.get('name')}」保存的配置覆盖当前编辑内容？"
                                ) != QMessageBox.StandardButton.Yes:
            return
        keep = self.session.baselines
        self.session.state.update({k: v for k, v in b["config"].items()})
        self.session.state["baselines"] = keep
        self.session.touch(chars=True, editor=True, selection=True, immediate=True)
        self.editor.refresh_sidebar()

    # ------------------------------------------------------------------ 窗口

    def _restore_geometry(self) -> None:
        geo = self.settings.get("windowGeometry")
        if isinstance(geo, str) and geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
            except (ValueError, TypeError):
                pass

    def closeEvent(self, ev) -> None:
        if self.stack.currentWidget() is self.editor_host and self.session.dirty:
            box = QMessageBox(self)
            box.setWindowTitle("退出")
            box.setText(f"配置「{self.session.config_name}」有未保存的修改。")
            save = box.addButton("保存并退出", QMessageBox.ButtonRole.AcceptRole)
            drop = box.addButton("不保存退出", QMessageBox.ButtonRole.DestructiveRole)
            box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked is save:
                self.session.save()
                self.session.capture_history()
            elif clicked is not drop:
                ev.ignore()
                return
            else:
                self.session.discard()
        try:
            self.storage.update_settings(
                windowGeometry=bytes(self.saveGeometry().toBase64()).decode("ascii"))
        except OSError:
            pass
        super().closeEvent(ev)


def run() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Gi DMG")
    app.setApplicationDisplayName(APP_TITLE)
    app.setOrganizationName("Gi DMG")
    app.setFont(theme.ui_font(9.5))
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(icons.app_icon())

    win = MainWindow()
    win.show()
    return app.exec()
