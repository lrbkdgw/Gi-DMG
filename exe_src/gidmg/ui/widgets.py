"""通用控件：卡片、开关、数字输入、下拉框、标签页头等。

这些控件把 HTML 版的 .gc/.sc/.pi/.tgl/.chip/.pill 等样式映射到 Qt，
让各面板代码可以像写 HTML 一样拼装界面。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, QSize, Qt,
                            Property, Signal)
from PySide6.QtGui import QColor, QCursor, QDoubleValidator, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox, QFrame, QGraphicsDropShadowEffect,
                               QHBoxLayout, QLabel, QLayout, QLineEdit, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import icons, theme
from ..core.state import num, numz


# ------------------------------------------------------------------ 布局助手

def vbox(parent: Optional[QWidget] = None, margins: Tuple[int, int, int, int] = (0, 0, 0, 0),
         spacing: int = 0) -> QVBoxLayout:
    lay = QVBoxLayout(parent) if parent is not None else QVBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def hbox(parent: Optional[QWidget] = None, margins: Tuple[int, int, int, int] = (0, 0, 0, 0),
         spacing: int = 0) -> QHBoxLayout:
    lay = QHBoxLayout(parent) if parent is not None else QHBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def shadow(widget: QWidget, blur: int = 22, dy: int = 4, alpha: int = 16) -> QWidget:
    """近似 CSS 的 --studio-shadow。"""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(22, 31, 48, alpha))
    widget.setGraphicsEffect(eff)
    return widget


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


# ------------------------------------------------------------------ 卡片

class Card(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, kind: str = "Card",
                 padding: int = 20, spacing: int = 12, with_shadow: bool = True):
        super().__init__(parent)
        self.setObjectName(kind)
        self.body = vbox(self, (padding, padding, padding, padding), spacing)
        if with_shadow:
            shadow(self)

    def add(self, w: QWidget, stretch: int = 0) -> QWidget:
        self.body.addWidget(w, stretch)
        return w

    def add_layout(self, lay: QLayout) -> QLayout:
        self.body.addLayout(lay)
        return lay


class SoftCard(Card):
    def __init__(self, parent=None, padding: int = 12, spacing: int = 8):
        super().__init__(parent, "SoftCard", padding, spacing, with_shadow=False)


class SubCard(Card):
    def __init__(self, parent=None, padding: int = 14, spacing: int = 10):
        super().__init__(parent, "SubCard", padding, spacing, with_shadow=False)


class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


# ------------------------------------------------------------------ 文本

def label(text: str, kind: str = "", parent: Optional[QWidget] = None,
          wrap: bool = False) -> QLabel:
    lb = QLabel(text, parent)
    if kind:
        lb.setObjectName(kind)
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    return lb


class Pill(QLabel):
    """圆角小标签，可带元素/反应配色。"""

    def __init__(self, text: str = "", color: str = theme.MUTED,
                 bg: Optional[str] = None, parent=None, bold: bool = True):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_color(color, bg, bold)

    def set_color(self, color: str, bg: Optional[str] = None, bold: bool = True) -> None:
        if bg is None:
            c = QColor(color)
            bg = f"rgba({c.red()},{c.green()},{c.blue()},0.11)"
        self.setStyleSheet(
            f"color:{color};background:{bg};border-radius:9px;padding:2px 8px;"
            f"font-size:10.5px;font-weight:{700 if bold else 500};")


class ElementPill(Pill):
    def __init__(self, elem: str, text: str = "", parent=None):
        from ..core.constants import EL_BY_ID
        super().__init__(text or EL_BY_ID.get(elem, {}).get("n", elem),
                         theme.element_color(elem), parent=parent)


# ------------------------------------------------------------------ 开关（.tgl）

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None, scale: float = 1.0):
        super().__init__(parent)
        self._w, self._h = int(36 * scale), int(20 * scale)
        self._knob = int(14 * scale)
        self._pad = int(3 * scale)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self.setFixedSize(self._w, self._h)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._anim = QPropertyAnimation(self, b"knobPos", self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_knob_pos(self) -> float:
        return self._pos

    def set_knob_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    knobPos = Property(float, get_knob_pos, set_knob_pos)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool, animate: bool = True) -> None:
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(1.0 if value else 0.0)
            self._anim.start()
        else:
            self.set_knob_pos(1.0 if value else 0.0)

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        ev.accept()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        off, on = QColor("#cfd5dd"), QColor(theme.BLUE)
        if not self.isEnabled():
            off, on = QColor("#e4e7ec"), QColor("#a8c0e8")
        track = QColor(
            round(off.red() + (on.red() - off.red()) * self._pos),
            round(off.green() + (on.green() - off.green()) * self._pos),
            round(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 0, self._w, self._h, self._h / 2, self._h / 2)
        travel = self._w - self._knob - self._pad * 2
        x = self._pad + travel * self._pos
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRect(int(x), self._pad, self._knob, self._knob))
        p.end()


class LabeledToggle(QWidget):
    """标题 + 说明 + 右侧开关，对应设置弹窗里的一行。"""
    toggled = Signal(bool)

    def __init__(self, title: str, hint: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        lay = hbox(self, (0, 0, 0, 0), 12)
        col = vbox(spacing=2)
        col.addWidget(label(title, "FieldLabel"))
        if hint:
            h = label(hint, "Muted", wrap=True)
            col.addWidget(h)
        lay.addLayout(col, 1)
        self.toggle = ToggleSwitch(checked)
        lay.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        self.toggle.toggled.connect(self.toggled.emit)

    def isChecked(self) -> bool:
        return self.toggle.isChecked()

    def setChecked(self, v: bool, animate: bool = True) -> None:
        self.toggle.setChecked(v, animate)


# ------------------------------------------------------------------ 输入

class NumField(QLineEdit):
    """数字输入。

    保持 HTML 的语义：内容为空/非法时按默认值处理（JS 的 `+x || default`）。
    """
    edited = Signal(float)

    def __init__(self, value: Any = 0, default: float = 0.0, parent=None,
                 decimals: int = 3, allow_negative: bool = True,
                 placeholder: str = "", width: Optional[int] = None,
                 zero_ok: bool = True):
        super().__init__(parent)
        self._default = default
        self._zero_ok = zero_ok
        val = QDoubleValidator(self)
        val.setNotation(QDoubleValidator.Notation.StandardNotation)
        val.setDecimals(decimals)
        if not allow_negative:
            val.setBottom(0.0)
        self.setValidator(val)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if placeholder:
            self.setPlaceholderText(placeholder)
        if width:
            self.setFixedWidth(width)
        self.set_value(value)
        self.textEdited.connect(lambda _t: self.edited.emit(self.value()))

    def value(self) -> float:
        return numz(self.text()) if self._zero_ok else num(self.text(), self._default)

    def set_value(self, value: Any) -> None:
        try:
            f = float(value)
        except (TypeError, ValueError):
            f = self._default
        txt = str(int(f)) if f == int(f) and abs(f) < 1e15 else f"{f:g}"
        if txt != self.text():
            blocked = self.blockSignals(True)
            self.setText(txt)
            self.blockSignals(blocked)


class TextField(QLineEdit):
    def __init__(self, text: str = "", placeholder: str = "", parent=None,
                 width: Optional[int] = None):
        super().__init__(text, parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        if width:
            self.setFixedWidth(width)


class Select(QComboBox):
    """带 (值, 文本) 映射的下拉框。"""
    picked = Signal(str)

    def __init__(self, options: Sequence[Tuple[str, str]] = (), value: str = "",
                 parent=None, width: Optional[int] = None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_options(options, value)
        if width:
            self.setFixedWidth(width)
        self.currentIndexChanged.connect(
            lambda _i: self.picked.emit(self.value()))

    def set_options(self, options: Sequence[Tuple[str, str]], value: str = "") -> None:
        blocked = self.blockSignals(True)
        self.clear()
        for key, text in options:
            self.addItem(text, key)
        self.set_value(value)
        self.blockSignals(blocked)

    def value(self) -> str:
        data = self.currentData()
        return "" if data is None else str(data)

    def set_value(self, value: str) -> None:
        idx = self.findData(value)
        blocked = self.blockSignals(True)
        self.setCurrentIndex(idx if idx >= 0 else 0)
        self.blockSignals(blocked)


def field(label_text: str, widget: QWidget, hint: str = "", spacing: int = 5) -> QWidget:
    """竖排的「标签 + 控件 (+ 说明)」。"""
    box = QWidget()
    lay = vbox(box, (0, 0, 0, 0), spacing)
    lay.addWidget(label(label_text, "FieldLabel"))
    lay.addWidget(widget)
    if hint:
        lay.addWidget(label(hint, "Muted", wrap=True))
    return box


# ------------------------------------------------------------------ 按钮

def button(text: str = "", icon_name: str = "", kind: str = "", parent=None,
           on_click: Optional[Callable[[], None]] = None, tooltip: str = "",
           icon_color: Optional[str] = None, icon_size: int = 15) -> QPushButton:
    b = QPushButton(text, parent)
    if kind:
        b.setObjectName(kind)
    if icon_name:
        color = icon_color or {
            "Primary": "#ffffff", "Tonal": theme.BLUE, "DangerBtn": theme.DANGER,
        }.get(kind, theme.MUTED)
        b.setIcon(icons.icon(icon_name, icon_size, color))
        b.setIconSize(QSize(icon_size, icon_size))
    if tooltip:
        b.setToolTip(tooltip)
    b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


def icon_button(icon_name: str, tooltip: str = "", parent=None,
                on_click: Optional[Callable[[], None]] = None,
                color: str = theme.MUTED, size: int = 16,
                kind: str = "IconBtn") -> QPushButton:
    b = QPushButton(parent)
    b.setObjectName(kind)
    b.setIcon(icons.icon(icon_name, size, color))
    b.setIconSize(QSize(size, size))
    b.setToolTip(tooltip)
    b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


def chip(text: str, parent=None, on_click: Optional[Callable[[], None]] = None,
         checkable: bool = False, icon_name: str = "") -> QPushButton:
    b = button(text, icon_name, "Chip", parent, on_click, icon_size=12)
    b.setCheckable(checkable)
    return b


# ------------------------------------------------------------------ 流式布局（标签墙）

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin: int = 0, h_spacing: int = 5, v_spacing: int = 5):
        super().__init__(parent)
        self._items: List[Any] = []
        self._hs, self._vs = h_spacing, v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._layout(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._layout(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect: QRect, apply: bool) -> int:
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        right = rect.right() - m.right()
        line_h = 0
        for it in self._items:
            hint = it.sizeHint()
            if x > rect.x() + m.left() and x + hint.width() > right:
                x = rect.x() + m.left()
                y += line_h + self._vs
                line_h = 0
            if apply:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._hs
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


# ------------------------------------------------------------------ 滚动容器

class ScrollArea(QScrollArea):
    def __init__(self, parent=None, margins=(0, 0, 0, 0), spacing: int = 0):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inner = QWidget()
        self.inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.body = vbox(self.inner, margins, spacing)
        self.setWidget(self.inner)

    def add(self, w: QWidget, stretch: int = 0) -> QWidget:
        self.body.addWidget(w, stretch)
        return w


# ------------------------------------------------------------------ 空状态

class EmptyState(QWidget):
    def __init__(self, icon_name: str, title: str, hint: str = "", parent=None,
                 action: Optional[QPushButton] = None):
        super().__init__(parent)
        lay = vbox(self, (24, 48, 24, 48), 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel()
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(icons.pixmap(icon_name, 20, theme.BLUE))
        badge.setStyleSheet(f"background:{theme.BLUE_TINT};border-radius:14px;")
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(12)

        t = label(title)
        t.setStyleSheet(f"color:{theme.TEXT};font-size:16px;font-weight:700;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        if hint:
            lay.addSpacing(4)
            h = label(hint, "Copy", wrap=True)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(h)
        if action is not None:
            lay.addSpacing(16)
            lay.addWidget(action, 0, Qt.AlignmentFlag.AlignHCenter)


# ------------------------------------------------------------------ 悬停转发

class HoverFilter(QEvent):
    pass


def on_hover(widget: QWidget, enter: Callable[[], None], leave: Callable[[], None]) -> None:
    """给任意控件挂上进入/离开回调（动态岛悬停展开用）。"""

    class _Filter(QWidget):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Type.Enter:
                enter()
            elif ev.type() == QEvent.Type.Leave:
                leave()
            return False

    f = _Filter(widget)
    f.hide()
    widget.installEventFilter(f)
    widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    setattr(widget, "_hover_filter", f)
