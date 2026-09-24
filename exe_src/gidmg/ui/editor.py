"""编辑器主界面：左侧导航 / 中央工作区 / 右侧统计，布局与 HTML 版一致。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (QButtonGroup, QFrame, QLabel, QPushButton, QSizePolicy,
                               QStackedWidget, QWidget)

from ..core.constants import EL_BY_ID
from . import icons, motion, theme, widgets as W
from .panels_character import CharacterPanel
from .panels_monster import MonsterPanel
from .panels_results import ResultsPanel
from .panels_timeline import TimelinePanel
from .session import Session
from .widgets import button, chip, clear_layout, hbox, icon_button, label, vbox

LEFT_W = 264
RIGHT_W = 324


class CharRow(QFrame):
    """左侧角色列表的一行（对应 HTML 的 .sidebar-character-row）。

    34px 高的胶囊，背景色在 hover / 选中之间补间，元素图标直接透明摆放，
    名称与状态同一行（HTML 里是 `align-items: baseline` 的两个 span）。
    """

    picked = Signal(str)
    toggled = Signal(str, bool)
    menuRequested = Signal(str)

    NAME_COLOR = "#43474e"
    STATUS_COLOR = "#9aa1ab"
    STATUS_ACTIVE = "#5581ce"

    def __init__(self, c: Dict[str, Any], active: bool, parent=None):
        super().__init__(parent)
        self.char_id = c["id"]
        self.setObjectName("CharRow")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(34)
        self._name = str(c.get("name", ""))
        self._status = "已启用" if c.get("on") else "未计入"
        self._element = c.get("element", "pyro")
        self._active = bool(active)
        self._active_t = motion.Tween(self, lambda _v: self.update(), motion.CONTROL)
        self._active_t.to(1.0 if active else 0.0, animate=False)
        self._hover = motion.HoverTracker(self, motion.CONTROL)

        lay = hbox(self, (8, 4, 8, 4), 8)
        lay.addSpacing(24)                       # 元素图标（自绘）占位
        lay.addStretch(1)
        self.toggle = W.ToggleSwitch(bool(c.get("on")))
        self.toggle.setToolTip("停用角色" if c.get("on") else "启用角色")
        self.toggle.toggled.connect(lambda v: self.toggled.emit(self.char_id, v))
        lay.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self._active_t.to(1.0 if active else 0.0)

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        act = self._active_t.value
        bg = motion.mix_color(QColor(0, 0, 0, 0), theme.SURFACE_SUBTLE, self._hover.hover)
        bg = motion.mix_color(bg, theme.BLUE_TINT, act)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        pm = icons.element_pixmap(self._element, 18)
        p.drawPixmap(QPointF(8 + (24 - 18) / 2, rect.center().y() - 9), pm)

        x = 8 + 24 + 8
        name_font = QFont(self.font())
        name_font.setPixelSize(13)
        status_font = QFont(self.font())
        status_font.setPixelSize(10)
        fm_n, fm_s = QFontMetrics(name_font), QFontMetrics(status_font)
        toggle_w = self.toggle.width() + 8
        avail = rect.right() - toggle_w - x - fm_s.horizontalAdvance(self._status) - 6

        p.setFont(name_font)
        p.setPen(motion.mix_color(self.NAME_COLOR, theme.BLUE, act))
        name = fm_n.elidedText(self._name, Qt.TextElideMode.ElideRight, int(max(16, avail)))
        p.drawText(QRectF(x, rect.top(), max(16.0, avail), rect.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), name)

        p.setFont(status_font)
        p.setPen(motion.mix_color(self.STATUS_COLOR, self.STATUS_ACTIVE, act))
        sx = x + fm_n.horizontalAdvance(name) + 6
        p.drawText(QRectF(sx, rect.top(), max(10.0, rect.right() - toggle_w - sx),
                          rect.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   self._status)
        p.end()

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
        self.workspace = "character"
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
        self._fader = motion.StackFader(self.stack)     # 换页淡入
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
        b = W.MotionButton(text, "NavEntry")
        b.set_icon(icon_name, None, 15)       # 图标颜色跟随文字一起过渡
        b.setCheckable(checkable)
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
        self.workspace = key if key in navs else "character"
        self._fader.switch(index)
        nav.setChecked(True)
        self.scroll.verticalScrollBar().setValue(0)
        # HTML 在魔物 / 时间轴工作区里会把角色行的选中高亮收起
        self._sync_char_active()

    def _sync_char_active(self) -> None:
        sel = self.s.state.get("selId")
        for row in self.char_scroll.inner.findChildren(CharRow):
            row.set_active(self.workspace == "character" and row.char_id == sel)

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
                active = c["id"] == sel and self.workspace == "character"
                row = CharRow(c, active, self.char_scroll.inner)
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
            c.set_skin(fg=theme.MUTED, hover_bg=theme.SURFACE_SUBTLE, hover_fg=theme.MUTED)
            c.set_static(True)
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
