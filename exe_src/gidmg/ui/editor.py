"""编辑器主界面：左侧导航 / 中央工作区 / 右侧统计，布局与 HTML 版一致。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QButtonGroup, QFrame, QLabel, QPushButton, QSizePolicy,
                               QStackedWidget, QWidget)

from ..core.constants import EL_BY_ID
from . import icons, theme, widgets as W
from .panels_character import CharacterPanel
from .panels_monster import MonsterPanel
from .panels_results import ResultsPanel
from .panels_timeline import TimelinePanel
from .session import Session
from .widgets import button, chip, clear_layout, hbox, icon_button, label, vbox

LEFT_W = 264
RIGHT_W = 324


class CharRow(QFrame):
    """左侧角色列表的一行。"""

    picked = Signal(str)
    toggled = Signal(str, bool)
    menuRequested = Signal(str)

    def __init__(self, c: Dict[str, Any], active: bool, parent=None):
        super().__init__(parent)
        self.char_id = c["id"]
        self.setObjectName("CharRow")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        bg = theme.BLUE_TINT if active else "transparent"
        border = theme.BLUE_BORDER if active else "transparent"
        self.setStyleSheet(f"""
            QFrame#CharRow {{ background:{bg}; border:1px solid {border}; border-radius:12px; }}
            QFrame#CharRow:hover {{ background:{theme.BLUE_TINT if active else theme.SURFACE_SUBTLE}; }}
        """)
        lay = hbox(self, (8, 6, 8, 6), 9)

        badge = QLabel()
        badge.setFixedSize(30, 30)
        badge.setPixmap(icons.element_badge(c.get("element", "pyro"), 30))
        badge.setStyleSheet("background:transparent;")
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        col = vbox(spacing=1)
        name = label(str(c.get("name", "")))
        name.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;"
                           "background:transparent;")
        col.addWidget(name)
        status = label("已启用" if c.get("on") else "未计入")
        status.setStyleSheet(f"color:{'#5581ce' if active else theme.MUTED};font-size:10.5px;"
                             "background:transparent;")
        col.addWidget(status)
        lay.addLayout(col, 1)

        self.toggle = W.ToggleSwitch(bool(c.get("on")), scale=0.78)
        self.toggle.toggled.connect(lambda v: self.toggled.emit(self.char_id, v))
        lay.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(self.char_id)
        elif ev.button() == Qt.MouseButton.RightButton:
            self.menuRequested.emit(self.char_id)
        ev.accept()


class EditorView(QWidget):
    """配置编辑主界面。"""

    openHistory = Signal()
    openSettings = Signal()
    openQuickSetter = Signal()
    openDetails = Signal()
    openDmgShare = Signal()
    inspectSource = Signal(str)
    viewBaseline = Signal(str)
    restoreBaseline = Signal(str)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        self.setObjectName("Canvas")
        root = hbox(self, (0, 0, 0, 0), 0)

        # ------------------------------------------------ 左栏
        self.left = QWidget()
        self.left.setFixedWidth(LEFT_W)
        self.left.setObjectName("LeftBar")
        self.left.setStyleSheet(f"QWidget#LeftBar {{ background:{theme.SURFACE}; "
                                f"border-right:1px solid {theme.BORDER}; }}")
        left_lay = vbox(self.left, (0, 0, 0, 0), 0)

        nav_top = QWidget()
        nl = vbox(nav_top, (12, 12, 12, 10), 4)
        self.nav_monster = self._nav("shield", "魔物设置")
        nl.addWidget(self.nav_monster)
        left_lay.addWidget(nav_top)
        left_lay.addWidget(self._hline())

        char_part = QWidget()
        cl = vbox(char_part, (12, 10, 12, 8), 6)
        head = hbox(spacing=8)
        self.nav_chars = self._nav("users-round", "角色")
        head.addWidget(self.nav_chars, 1)
        self.add_char_btn = icon_button("plus", "新增角色", char_part,
                                        lambda: self.s.add_char(), theme.BLUE, 15, "AddBtn")
        head.addWidget(self.add_char_btn)
        cl.addLayout(head)

        self.char_scroll = W.ScrollArea(margins=(0, 0, 2, 0), spacing=4)
        cl.addWidget(self.char_scroll, 1)
        self.char_scroll.body.addStretch(1)

        cl.addWidget(self._subhead("元素共鸣"))
        self.reso_host = QWidget()
        self.reso_flow = W.FlowLayout(self.reso_host, h_spacing=4, v_spacing=4)
        cl.addWidget(self.reso_host)
        left_lay.addWidget(char_part, 1)
        left_lay.addWidget(self._hline())

        nav_bottom = QWidget()
        bl = vbox(nav_bottom, (12, 10, 12, 12), 4)
        self.nav_history = self._nav("history", "历史记录", checkable=False)
        self.nav_history.clicked.connect(self.openHistory.emit)
        bl.addWidget(self.nav_history)
        self.nav_timeline = self._nav("clock-3", "时间轴")
        bl.addWidget(self.nav_timeline)
        left_lay.addWidget(nav_bottom)
        root.addWidget(self.left)

        # ------------------------------------------------ 中栏
        center = QWidget()
        center.setObjectName("Canvas")
        cen_lay = vbox(center, (0, 0, 0, 0), 0)
        self.scroll = W.ScrollArea(margins=(32, 44, 32, 40), spacing=0)
        cen_lay.addWidget(self.scroll, 1)

        self.stack = QStackedWidget()
        self.stack.setMaximumWidth(930)
        self.stack.setMinimumWidth(520)
        holder = hbox(spacing=0)
        holder.addStretch(1)
        holder.addWidget(self.stack, 1000)
        holder.addStretch(1)
        self.scroll.body.addLayout(holder)

        self.panel_character = CharacterPanel(session)
        self.panel_character.openQuickSetter.connect(self.openQuickSetter.emit)
        self.panel_monster = MonsterPanel(session)
        self.panel_timeline = TimelinePanel(session)
        self.panel_timeline.openSettings.connect(self.openSettings.emit)
        self.panel_timeline.jump.connect(self._jump_to_source)
        for p in (self.panel_character, self.panel_monster, self.panel_timeline):
            self.stack.addWidget(p)
        root.addWidget(center, 1)

        # ------------------------------------------------ 右栏
        self.results = ResultsPanel(session)
        self.results.setFixedWidth(RIGHT_W)
        self.results.inspectSource.connect(self.inspectSource.emit)
        self.results.showDetails.connect(self.openDetails.emit)
        self.results.showDmgShare.connect(self.openDmgShare.emit)
        self.results.viewBaseline.connect(self.viewBaseline.emit)
        self.results.restoreBaseline.connect(self.restoreBaseline.emit)
        root.addWidget(self.results)

        # ------------------------------------------------ 导航分组
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, b in enumerate((self.nav_chars, self.nav_monster, self.nav_timeline)):
            self.nav_group.addButton(b, i)
        self.nav_chars.setChecked(True)
        self.nav_chars.clicked.connect(lambda: self.set_workspace("character"))
        self.nav_monster.clicked.connect(lambda: self.set_workspace("monster"))
        self.nav_timeline.clicked.connect(lambda: self.set_workspace("timeline"))

        session.charsChanged.connect(self.refresh_sidebar)
        session.selectionChanged.connect(self.refresh_sidebar)
        session.calcFinished.connect(self._sync_nav)
        self.refresh_sidebar()

    # ------------------------------------------------------------------ 构件

    def _nav(self, icon_name: str, text: str, checkable: bool = True) -> QPushButton:
        b = QPushButton(f"  {text}")
        b.setObjectName("NavEntry")
        b.setIcon(icons.icon(icon_name, 15, "#4f5966", active_color=theme.BLUE))
        b.setIconSize(QSize(15, 15))
        b.setCheckable(checkable)
        b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return b

    def _hline(self) -> QFrame:
        f = QFrame()
        f.setFixedHeight(1)
        f.setStyleSheet(f"background:{theme.BORDER_SOFT};")
        return f

    def _subhead(self, text: str) -> QLabel:
        lb = label(text)
        lb.setStyleSheet(f"color:{theme.MUTED};font-size:10.5px;font-weight:700;"
                         "padding:6px 5px 2px;")
        return lb

    # ------------------------------------------------------------------ 状态

    def set_workspace(self, key: str) -> None:
        navs = {"character": (0, self.nav_chars), "monster": (1, self.nav_monster),
                "timeline": (2, self.nav_timeline)}
        index, nav = navs.get(key, navs["character"])
        self.stack.setCurrentIndex(index)
        nav.setChecked(True)
        self.scroll.verticalScrollBar().setValue(0)

    def set_quick_table_mode(self, on: bool) -> None:
        self.add_char_btn.setVisible(not on)
        self.panel_character.set_quick_table_mode(on)

    def refresh_sidebar(self) -> None:
        # 角色列表
        lay = self.char_scroll.body
        clear_layout(lay)
        chars = self.s.chars
        if not chars:
            lb = label("尚未添加角色。", "Muted")
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:12px;padding:8px 6px;")
            lay.addWidget(lb)
        else:
            sel = self.s.state.get("selId")
            for c in chars:
                row = CharRow(c, c["id"] == sel, self.char_scroll.inner)
                row.picked.connect(self._pick_char)
                row.toggled.connect(self._toggle_char)
                row.menuRequested.connect(self._char_menu)
                lay.addWidget(row)
        lay.addStretch(1)

        # 元素共鸣
        clear_layout(self.reso_flow)
        resos = self.s.resonances()
        if not resos:
            lb = label("暂无共鸣", "Muted")
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:10.5px;")
            self.reso_flow.addWidget(lb)
        for item in resos:
            c = chip(item["text"], self.reso_host)
            ids = item.get("ids") or [item.get("id")]
            first = ids[0] if ids else "pyro"
            c.setIcon(icons.element_icon(first, 12))
            c.setIconSize(QSize(12, 12))
            c.setEnabled(False)
            c.setStyleSheet(
                f"QPushButton {{ color:{theme.MUTED}; background:{theme.SURFACE_SUBTLE};"
                f"border:1px solid transparent; border-radius:999px; padding:2px 8px;"
                f"font-size:10px; }}")
            self.reso_flow.addWidget(c)

    def _sync_nav(self) -> None:
        self.nav_timeline.setEnabled(True)

    # ------------------------------------------------------------------ 交互

    def _pick_char(self, char_id: str) -> None:
        self.s.select(char_id)
        self.set_workspace("character")
        self.refresh_sidebar()

    def _toggle_char(self, char_id: str, value: bool) -> None:
        c = self.s.char(char_id)
        if c is not None:
            c["on"] = value
            self.s.touch(chars=True, immediate=True)
            self.refresh_sidebar()

    def _char_menu(self, char_id: str) -> None:
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction(icons.muted("copy", 14), "复制角色", lambda: self.s.duplicate_char(char_id))
        m.addSeparator()
        m.addAction(icons.icon("trash-2", 14, theme.DANGER), "删除角色",
                    lambda: self.s.remove_char(char_id))
        m.exec(QCursor.pos())

    def _jump_to_source(self, char_id: str, _source_id: str) -> None:
        self.s.select(char_id)
        self.set_workspace("character")
        self.refresh_sidebar()
