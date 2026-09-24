"""历史记录弹窗：配置历史 + 拉表结果历史（对应 HTML historyModal）。"""

from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QMessageBox, QTabWidget, QWidget

from ...core import quicktable as qt
from ...core.format import hist_time, rounded
from .. import icons, theme, widgets as W
from ..session import Session
from ..widgets import button, clear_layout, hbox, icon_button, label, vbox
from .base import Modal


class HistoryDialog(Modal):
    def __init__(self, parent, session: Session):
        super().__init__(parent, "历史记录", "history", width=620, height=620)
        self.s = session
        self.parent_window = parent

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; }}
            QTabBar::tab {{ padding:7px 14px; margin-right:4px; color:{theme.MUTED};
                            background:{theme.SURFACE_SUBTLE}; border:none;
                            border-radius:999px; font-size:12px; }}
            QTabBar::tab:selected {{ color:{theme.BLUE}; background:{theme.BLUE_TINT};
                                     font-weight:600; }}
        """)
        self.cfg_page = QWidget()
        self.cfg_lay = vbox(self.cfg_page, (0, 8, 0, 0), 7)
        self.qt_page = QWidget()
        self.qt_lay = vbox(self.qt_page, (0, 8, 0, 0), 7)
        tabs.addTab(self.cfg_page, "配置历史")
        tabs.addTab(self.qt_page, "拉表结果")
        self.add(tabs, 1)

        self.add_button("清空当前列表", "trash-2", "DangerBtn", self._clear)
        self.add_button("关闭", "", "", self.accept)
        self.tabs = tabs
        self.reload()

    # ------------------------------------------------------------------

    def reload(self) -> None:
        clear_layout(self.cfg_lay)
        cfg = self.s.storage.load_cfg_history()
        if not cfg:
            self.cfg_lay.addWidget(self._empty("暂无配置历史。退出配置时会自动记录一次。"))
        for rec in cfg:
            self.cfg_lay.addWidget(self._cfg_row(rec))
        self.cfg_lay.addStretch(1)

        clear_layout(self.qt_lay)
        qth = self.s.storage.load_qt_history()
        if not qth:
            self.qt_lay.addWidget(self._empty("暂无拉表历史。完成一次快速拉表后会自动保存。"))
        for rec in qth:
            self.qt_lay.addWidget(self._qt_row(rec))
        self.qt_lay.addStretch(1)

    def _empty(self, text: str):
        lb = label(text, "Muted", wrap=True)
        lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:12px;padding:16px 4px;")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lb

    def _row_frame(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background:{theme.SURFACE_SUBTLE}; border:1px solid transparent;"
                        f"border-radius:12px; }} QFrame:hover {{ border-color:{theme.BLUE_BORDER}; }}")
        return f

    def _cfg_row(self, rec: Dict[str, Any]) -> QFrame:
        f = self._row_frame()
        lay = hbox(f, (12, 9, 10, 9), 10)
        col = vbox(spacing=3)
        t = label(f"{rec.get('configName') or '未命名配置'} · {hist_time(rec.get('time'))}")
        t.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        col.addWidget(t)
        sub = label(f"{rec.get('charNames') or '无角色'} · 总期望 {rounded(rec.get('total', 0))}", "Muted")
        col.addWidget(sub)
        lay.addLayout(col, 1)
        lay.addWidget(button("恢复", "rotate-ccw", "Tonal", f, lambda: self._restore(rec)))
        lay.addWidget(icon_button("trash-2", "删除该记录", f,
                                  lambda: self._delete_cfg(rec.get("id"))))
        return f

    def _qt_row(self, rec: Dict[str, Any]) -> QFrame:
        f = self._row_frame()
        lay = hbox(f, (12, 9, 10, 9), 10)
        col = vbox(spacing=3)
        t = label(hist_time(rec.get("time")))
        t.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        col.addWidget(t)
        col.addWidget(label(f"{rec.get('count', 0)} 种组合 · 最高 DPS "
                            f"{rounded(rec.get('bestDps', 0))}", "Muted"))
        lay.addLayout(col, 1)
        lay.addWidget(button("查看", "table", "Tonal", f, lambda: self._view_qt(rec)))
        lay.addWidget(icon_button("trash-2", "删除该记录", f,
                                  lambda: self._delete_qt(rec.get("id"))))
        return f

    # ------------------------------------------------------------------

    def _restore(self, rec: Dict[str, Any]) -> None:
        cfg = rec.get("config")
        if not isinstance(cfg, dict):
            return
        if QMessageBox.question(self, "恢复历史配置",
                                "用这条历史记录覆盖当前编辑中的配置？"
                                ) != QMessageBox.StandardButton.Yes:
            return
        keep = self.s.baselines
        self.s.state.update(cfg)
        self.s.state["baselines"] = keep
        self.s.touch(chars=True, editor=True, selection=True, immediate=True)
        self.accept()

    def _view_qt(self, rec: Dict[str, Any]) -> None:
        from .quicktable import show_results
        rows = [qt.QtResult.from_json(r) for r in rec.get("results", [])]
        info = rec.get("charInfo", [])
        self.accept()
        show_results(self.parent_window, self.s, rows, info)

    def _delete_cfg(self, rid: str) -> None:
        self.s.storage.save_cfg_history(
            [r for r in self.s.storage.load_cfg_history() if r.get("id") != rid])
        self.reload()

    def _delete_qt(self, rid: str) -> None:
        self.s.storage.save_qt_history(
            [r for r in self.s.storage.load_qt_history() if r.get("id") != rid])
        self.reload()

    def _clear(self) -> None:
        which = "配置历史" if self.tabs.currentIndex() == 0 else "拉表历史"
        if QMessageBox.question(self, "清空历史", f"确定清空全部{which}？"
                                ) != QMessageBox.StandardButton.Yes:
            return
        if self.tabs.currentIndex() == 0:
            self.s.storage.save_cfg_history([])
        else:
            self.s.storage.save_qt_history([])
        self.reload()


def open_history(parent, session: Session) -> None:
    HistoryDialog(parent, session).exec()
