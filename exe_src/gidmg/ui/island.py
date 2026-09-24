"""顶部居中的「灵动岛」。

对应 What_Change.md 第 3 / 5 条：
  · 平时显示当前配置名；
  · 点击后文字变成四个图标按钮：保存并退出 / 不保存并退出 / 快速拉表 / 设置；
  · 平时自动收起到窗口顶边，鼠标移上去再弹出。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, QSize,
                            QTimer, Qt, Signal)
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QStackedLayout, QWidget)

from . import icons, theme
from .widgets import hbox, vbox

COLLAPSED_PEEK = 5        # 收起时露在窗口顶边外的高度
ISLAND_HEIGHT = 34
ANIM_MS = 220


class _IslandButton(QPushButton):
    """灵动岛展开后的圆形图标按钮。"""

    def __init__(self, icon_name: str, tip: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setIcon(icons.icon(icon_name, 15, color))
        self.setIconSize(QSize(15, 15))
        self.setToolTip(tip)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        c = QColor(color)
        hover = f"rgba({c.red()},{c.green()},{c.blue()},0.13)"
        self.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 14px; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: rgba({c.red()},{c.green()},{c.blue()},0.22); }}
        """)


class DynamicIsland(QWidget):
    """悬浮在编辑器顶部中央的胶囊。"""

    saveExit = Signal()
    discardExit = Signal()
    quickTable = Signal()
    settings = Signal()
    renameRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("Island")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMouseTracking(True)

        self._expanded_actions = False   # 是否显示四个按钮
        self._peeking = False            # 是否已从顶边弹出
        self._dirty = False
        self._name = ""

        self.setStyleSheet(f"""
            QWidget#Island {{
                background: {theme.SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: {ISLAND_HEIGHT // 2}px;
            }}
        """)
        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(26)
        eff.setOffset(0, 6)
        eff.setColor(QColor(24, 37, 59, 42))
        self.setGraphicsEffect(eff)

        root = hbox(self, (4, 3, 4, 3), 0)

        # --- 收起态：配置名
        self.name_page = QWidget(self)
        name_lay = hbox(self.name_page, (10, 0, 10, 0), 7)
        self.dot = QLabel(self.name_page)
        self.dot.setFixedSize(7, 7)
        self._paint_dot(False)
        name_lay.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.name_label = QLabel("未命名配置", self.name_page)
        self.name_label.setStyleSheet(
            f"color:{theme.TEXT};font-size:12px;font-weight:600;background:transparent;")
        name_lay.addWidget(self.name_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hint = QLabel(self.name_page)
        self.hint.setPixmap(icons.pixmap("chevron-down", 13, theme.MUTED_SOFT))
        self.hint.setStyleSheet("background:transparent;")
        name_lay.addWidget(self.hint, 0, Qt.AlignmentFlag.AlignVCenter)

        # --- 展开态：四个图标按钮
        self.action_page = QWidget(self)
        act_lay = hbox(self.action_page, (3, 0, 3, 0), 2)
        self.btn_save = _IslandButton("save", "保存并退出", theme.BLUE, self.action_page)
        self.btn_discard = _IslandButton("log-out", "不保存并退出", theme.DANGER, self.action_page)
        self.btn_qt = _IslandButton("table-properties", "快速拉表", theme.WARN, self.action_page)
        self.btn_settings = _IslandButton("settings-2", "设置", theme.MUTED, self.action_page)
        for b in (self.btn_save, self.btn_discard, self.btn_qt, self.btn_settings):
            act_lay.addWidget(b)
        self.btn_save.clicked.connect(self.saveExit.emit)
        self.btn_discard.clicked.connect(self.discardExit.emit)
        self.btn_qt.clicked.connect(self.quickTable.emit)
        self.btn_settings.clicked.connect(self.settings.emit)

        self.pages = QStackedLayout()
        self.pages.setContentsMargins(0, 0, 0, 0)
        self.pages.addWidget(self.name_page)
        self.pages.addWidget(self.action_page)
        root.addLayout(self.pages)

        self.setFixedHeight(ISLAND_HEIGHT)
        self._geo_anim = QPropertyAnimation(self, b"geometry", self)
        self._geo_anim.setDuration(ANIM_MS)
        self._geo_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(900)
        self._collapse_timer.timeout.connect(self._maybe_collapse)

        if parent is not None:
            parent.installEventFilter(self)

    # ------------------------------------------------------------- 外部接口

    def set_config_name(self, name: str) -> None:
        self._name = name or "未命名配置"
        self._refresh_name()

    def set_dirty(self, dirty: bool) -> None:
        self._dirty = bool(dirty)
        self._paint_dot(self._dirty)
        self._refresh_name()

    def _refresh_name(self) -> None:
        text = self._name + (" ·未保存" if self._dirty else "")
        self.name_label.setText(text)
        self.name_label.setToolTip("点击展开操作按钮")
        self._reposition(animate=False)

    def _paint_dot(self, dirty: bool) -> None:
        color = theme.WARN if dirty else theme.OK
        self.dot.setStyleSheet(f"background:{color};border-radius:3px;")

    # ------------------------------------------------------------- 交互

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.set_actions_visible(not self._expanded_actions)
        ev.accept()

    def mouseDoubleClickEvent(self, ev) -> None:
        if not self._expanded_actions:
            self.renameRequested.emit()
        ev.accept()

    def set_actions_visible(self, visible: bool) -> None:
        if visible == self._expanded_actions:
            return
        self._expanded_actions = visible
        self.pages.setCurrentIndex(1 if visible else 0)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor if visible
                               else Qt.CursorShape.PointingHandCursor))
        self._reposition(animate=True)

    def peek(self, on: bool = True, animate: bool = True) -> None:
        """让灵动岛完全露出（True）或缩回顶边（False）。"""
        self._collapse_timer.stop()
        self._peeking = bool(on)
        self._reposition(animate=animate)

    def expand(self, animate: bool = True) -> None:
        """展开成四个图标按钮。"""
        self.peek(True, animate)
        self.set_actions_visible(True)
        if not animate:
            self._geo_anim.stop()
            self.setGeometry(self._target_rect())

    def collapse(self, animate: bool = True) -> None:
        """收起按钮并缩回顶边。"""
        self.set_actions_visible(False)
        self.peek(False, animate)
        if not animate:
            self._geo_anim.stop()
            self.setGeometry(self._target_rect())

    def enterEvent(self, ev) -> None:
        self._collapse_timer.stop()
        self._peeking = True
        self._reposition(animate=True)
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        self._collapse_timer.start()
        super().leaveEvent(ev)

    def _maybe_collapse(self) -> None:
        if self.underMouse():
            self._collapse_timer.start()
            return
        self._peeking = False
        self.set_actions_visible(False)
        self._reposition(animate=True)

    # ------------------------------------------------------------- 位置

    def _target_width(self) -> int:
        if self._expanded_actions:
            return 4 * 28 + 3 * 2 + 6 + 8
        text_w = self.name_label.fontMetrics().horizontalAdvance(self.name_label.text())
        return min(360, max(150, text_w + 62))

    def _target_rect(self) -> QRect:
        parent = self.parentWidget()
        if parent is None:
            return self.geometry()
        w = self._target_width()
        x = (parent.width() - w) // 2
        y = 8 if self._peeking else (COLLAPSED_PEEK - ISLAND_HEIGHT)
        return QRect(x, y, w, ISLAND_HEIGHT)

    def _reposition(self, animate: bool = True) -> None:
        target = self._target_rect()
        if target == self.geometry():
            return
        self._geo_anim.stop()
        if animate and self.isVisible():
            self._geo_anim.setStartValue(self.geometry())
            self._geo_anim.setEndValue(target)
            self._geo_anim.start()
        else:
            self.setGeometry(target)

    def eventFilter(self, obj, ev) -> bool:
        if obj is self.parentWidget():
            if ev.type() == QEvent.Type.Resize:
                self._reposition(animate=False)
            elif ev.type() == QEvent.Type.MouseMove:
                self._track_pointer(ev.position().toPoint())
        return False

    def _track_pointer(self, pos: QPoint) -> None:
        """鼠标靠近窗口顶部时自动弹出灵动岛。"""
        parent = self.parentWidget()
        if parent is None:
            return
        hot = QRect((parent.width() - 360) // 2, 0, 360, ISLAND_HEIGHT + 16)
        inside = hot.contains(pos)
        if inside and not self._peeking:
            self._collapse_timer.stop()
            self._peeking = True
            self._reposition(animate=True)
        elif not inside and self._peeking and not self.underMouse():
            self._collapse_timer.start()


class IslandHost(QWidget):
    """让灵动岛始终浮在内容之上的容器。"""

    def __init__(self, content: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Canvas")
        self.setMouseTracking(True)
        lay = vbox(self, (0, 0, 0, 0), 0)
        self.content = content
        content.setParent(self)
        lay.addWidget(content)
        self.island = DynamicIsland(self)
        self.island.raise_()

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self.island._reposition(animate=False)
        self.island.raise_()

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        self.island._reposition(animate=False)
        self.island.raise_()

    def mouseMoveEvent(self, ev) -> None:
        self.island._track_pointer(ev.position().toPoint())
        super().mouseMoveEvent(ev)
