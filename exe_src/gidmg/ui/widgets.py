"""通用控件：卡片、开关、数字输入、下拉框、标签页头等。

这些控件把 HTML 版的 .gc/.sc/.pi/.tgl/.chip/.pill 等样式映射到 Qt，
让各面板代码可以像写 HTML 一样拼装界面。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRect,
                            QRectF, QSize, Qt, Property, Signal)
from PySide6.QtGui import (QColor, QCursor, QDoubleValidator, QFont, QFontMetrics, QPainter,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QComboBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QLayout, QLineEdit, QPushButton, QScrollArea, QSlider,
                               QVBoxLayout, QWidget)

from . import icons, motion, theme
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
    """HTML `.tgl`：36×20 轨道 + 14px 白色圆钮，`transition: .2s ease`。"""

    toggled = Signal(bool)

    OFF = "#e2e5eb"
    OFF_HOVER = "#d5d9e1"

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
        self._anim.setDuration(motion.SLOW)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover = motion.HoverTracker(self, motion.SLOW)

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
        hover = self._hover.hover
        if self.isEnabled():
            off = motion.mix_color(self.OFF, self.OFF_HOVER, hover)
            on = motion.mix_color(theme.BLUE, theme.BLUE_HOVER, hover)
        else:
            off, on = QColor("#e8eaee"), QColor("#a8c0e8")
        track = motion.mix_color(off, on, self._pos)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, self._w, self._h), self._h / 2, self._h / 2)

        travel = self._w - self._knob - self._pad * 2
        x = self._pad + travel * self._pos
        knob_rect = QRectF(x, self._pad, self._knob, self._knob)
        # box-shadow: 0 1px 2px rgba(0,0,0,.15)
        shade = QColor(0, 0, 0, 34)
        p.setBrush(shade)
        p.drawEllipse(knob_rect.translated(0, 1))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(knob_rect)
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
        motion.focus_glow(self)
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
        motion.focus_glow(self)


class Select(QComboBox):
    """带 (值, 文本) 映射的下拉框。

    视觉对齐 HTML 的 `.studio-select`：悬停浅灰、展开时白底蓝边并带光晕，
    右侧箭头由 45° 旋到 225°，弹出的选项面板淡入并轻微下滑。
    """
    picked = Signal(str)

    def __init__(self, options: Sequence[Tuple[str, str]] = (), value: str = "",
                 parent=None, width: Optional[int] = None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._hover = motion.HoverTracker(self, motion.CONTROL)
        self._open_t = motion.Tween(self, lambda _v: self.update(), motion.CONTROL)
        motion.focus_glow(self)             # 展开/聚焦时的 0 0 0 3px 蓝色光晕
        self._popup_anim: Optional[QPropertyAnimation] = None
        self.set_options(options, value)
        if width:
            self.setFixedWidth(width)
        self.currentIndexChanged.connect(
            lambda _i: self.picked.emit(self.value()))

    # -------------------------------------------------- 数据

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

    # -------------------------------------------------- 展开 / 收起

    def showPopup(self) -> None:
        super().showPopup()
        self._open_t.to(1.0)
        view_win = self.view().window()
        if view_win is not None:
            start = view_win.geometry()
            self._popup_anim = QPropertyAnimation(view_win, b"geometry", self)
            self._popup_anim.setDuration(motion.CONTROL)
            self._popup_anim.setEasingCurve(motion.EASE)
            above = start.top() < self.mapToGlobal(QPoint(0, 0)).y()
            dy = 6 if not above else -6
            self._popup_anim.setStartValue(start.translated(0, -dy))
            self._popup_anim.setEndValue(start)
            self._popup_anim.start()

    def hidePopup(self) -> None:
        super().hidePopup()
        self._open_t.to(0.0)

    # -------------------------------------------------- 绘制

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        hover, open_t = self._hover.hover, self._open_t.value
        enabled = self.isEnabled()

        if not enabled:
            bg, border = QColor("#f5f6f8"), QColor(theme.BORDER_SOFT)
        else:
            bg = motion.mix_color(theme.SURFACE_SUBTLE, "#edf2f8", hover)
            border = motion.mix_color(theme.BORDER, "#ccd5e0", hover)
            bg = motion.mix_color(bg, theme.SURFACE, open_t)
            border = motion.mix_color(border, theme.BLUE, open_t)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, theme.RADIUS_SM, theme.RADIUS_SM)

        # 文本（带元素图标时先画图标）
        text = self.currentText()
        icon = self.itemIcon(self.currentIndex())
        x = rect.left() + 10
        if not icon.isNull():
            pm = icon.pixmap(self.iconSize())
            h = pm.height() / pm.devicePixelRatio()
            p.drawPixmap(QPointF(x, rect.center().y() - h / 2), pm)
            x += pm.width() / pm.devicePixelRatio() + 6
        if not enabled:
            fg = QColor("#9aa3ae")
        elif not text or not self.value():
            fg = QColor("#8a94a2")            # .studio-select.is-placeholder
        else:
            fg = QColor("#27303b")
        avail = rect.right() - 30 - x
        fm = QFontMetrics(self.font())
        p.setPen(fg)
        p.drawText(QRectF(x, rect.top(), max(10.0, avail), rect.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   fm.elidedText(text, Qt.TextElideMode.ElideRight, int(max(10, avail))))

        # 箭头：45° → 225°（与 .studio-select-trigger::after 一致）
        arrow = motion.mix_color("#657180", theme.BLUE, open_t) if enabled else QColor("#b6bcc6")
        p.save()
        p.translate(rect.right() - 14, rect.center().y() - motion.lerp(1.0, -1.0, open_t))
        p.rotate(45 + 180 * open_t)
        pen = QPen(arrow, 1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        s = 3.5
        p.drawLine(QPointF(s, -s), QPointF(s, s))
        p.drawLine(QPointF(-s, s), QPointF(s, s))
        p.restore()
        p.end()


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

# 每种按钮的配色，取值来自 HTML style2.css 里对应的 .bg / .bs / .bgh / .chip 等规则。
# 结构：background / border / text，以及 hover、pressed、checked 的变体。
BUTTON_SKINS: dict = {
    # .bs —— 次要按钮：描边胶囊，悬停填浅灰
    "": dict(bg="transparent", border=theme.BORDER, fg="#4f5a67",
             hover_bg=theme.SURFACE_SUBTLE, hover_border="#ccd4df", hover_fg=theme.TEXT,
             press_bg=theme.SURFACE_HOVER, radius=999),
    # .bg —— 主按钮：蓝底白字，悬停加深并轻微上浮
    "Primary": dict(bg=theme.BLUE, border=theme.BLUE, fg="#ffffff",
                    hover_bg=theme.BLUE_HOVER, hover_border=theme.BLUE_HOVER, hover_fg="#ffffff",
                    press_bg="#06316f", radius=999, lift=1.0, glow="rgba(11,87,208,0.30)",
                    disabled_bg="#9db7e4", disabled_border="#9db7e4", disabled_fg="#eef1f5"),
    "Tonal": dict(bg=theme.BLUE_TINT, border=theme.BLUE_BORDER, fg=theme.BLUE,
                  hover_bg=theme.BLUE_TINT_HOVER, hover_border="#c7d8f7", hover_fg=theme.BLUE,
                  press_bg="#cfe0ff", radius=999),
    "DangerBtn": dict(bg=theme.DANGER_TINT, border="#f7cfcb", fg=theme.DANGER,
                      hover_bg="#f9d6d3", hover_border="#f1bdb8", hover_fg=theme.DANGER,
                      press_bg="#f4c7c3", radius=999),
    # .bgh —— 幽灵按钮
    "Ghost": dict(bg="transparent", border="transparent", fg="#647080",
                  hover_bg=theme.SURFACE_SUBTLE, hover_border="transparent", hover_fg=theme.TEXT,
                  press_bg=theme.SURFACE_HOVER, radius=999),
    # 文字链接（hover 下划线，与网页 hover:underline 一致）
    "Link": dict(bg="transparent", border="transparent", fg=theme.BLUE,
                 hover_bg="transparent", hover_border="transparent", hover_fg=theme.BLUE_HOVER,
                 press_bg="transparent", radius=6, underline=True),
    # .chip
    "Chip": dict(bg=theme.SURFACE_SUBTLE, border="transparent", fg="#4f5966",
                 hover_bg=theme.BLUE_TINT, hover_border="transparent", hover_fg=theme.BLUE,
                 press_bg=theme.BLUE_TINT_HOVER, radius=999,
                 checked_bg="#dbe8ff", checked_border="#8ab0f0", checked_fg="#174ea6"),
    # .sidebar-icon-button
    "IconBtn": dict(bg="transparent", border="transparent", fg=theme.MUTED,
                    hover_bg=theme.SURFACE_SUBTLE, hover_border="transparent", hover_fg=theme.TEXT,
                    press_bg=theme.SURFACE_HOVER, radius=999, circular=True),
    # .sidebar-add-button
    "AddBtn": dict(bg=theme.BLUE_TINT, border=theme.BLUE_BORDER, fg=theme.BLUE,
                   hover_bg=theme.BLUE_TINT_HOVER, hover_border="#cdddf9", hover_fg=theme.BLUE,
                   press_bg="#cfe0ff", radius=999, circular=True),
    # .sidebar-entry —— 左侧导航胶囊
    "NavEntry": dict(bg="transparent", border="transparent", fg="#4f5966",
                     hover_bg=theme.SURFACE_SUBTLE, hover_border="transparent",
                     hover_fg=theme.TEXT, press_bg=theme.SURFACE_HOVER, radius=999,
                     checked_bg=theme.BLUE_TINT, checked_border="transparent",
                     checked_fg=theme.BLUE, align_left=True, pad=12),
}


class MotionButton(QPushButton):
    """自绘按钮：颜色按 hover / pressed 进度插值，复刻 CSS `transition: .15s ease`。

    尺寸、字号仍然走全局 QSS（`theme.stylesheet()` 里的 QPushButton 规则），
    这里只接管背景、描边、文字与图标的绘制，从而得到网页那样的渐变过渡。
    """

    def __init__(self, text: str = "", kind: str = "", parent=None):
        super().__init__(text, parent)
        self.kind = kind
        if kind:
            self.setObjectName(kind)
        self._skin = dict(BUTTON_SKINS.get(kind, BUTTON_SKINS[""]))
        self._icon_name = ""
        self._icon_color: Optional[str] = None
        self._icon_px = 15
        self._checked_tween = motion.Tween(self, lambda _v: self.update(), motion.BASE)
        self._hover = motion.HoverTracker(self, motion.BASE)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggled.connect(lambda on: self._checked_tween.to(1.0 if on else 0.0))
        if self._skin.get("lift"):
            self._shadow = QGraphicsDropShadowEffect(self)
            self._shadow.setOffset(0, 2)
            self._shadow.setBlurRadius(0.0)
            self._shadow.setColor(QColor(11, 87, 208, 70))
            self._shadow.setEnabled(False)
            self.setGraphicsEffect(self._shadow)
        else:
            self._shadow = None

    # -------------------------------------------------- 图标

    def set_icon(self, name: str, color: Optional[str] = None, size: int = 15) -> None:
        self._icon_name, self._icon_color, self._icon_px = name, color, size
        self.setIconSize(QSize(size, size))
        # 真的挂一个 QIcon，好让 Qt 的 sizeHint 把图标宽度算进去；
        # 绘制时仍按 _icon_name 重新着色，这样颜色能跟着 hover 过渡。
        super().setIcon(icons.icon(name, size, color or self._skin["fg"]))
        self.update()

    def set_skin(self, **overrides) -> None:
        """局部覆盖配色（例如结果列表里跟随元素色的名称按钮）。"""
        self._skin.update(overrides)
        self.update()

    def set_static(self, static: bool = True) -> None:
        """纯展示用：不再响应鼠标，也不做 hover 过渡。"""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, static)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus if static else Qt.FocusPolicy.StrongFocus)
        if static:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self._hover.reset()

    def sizeHint(self) -> QSize:
        s = super().sizeHint()
        if self._icon_name and self.text():
            s.setWidth(s.width() + 4)       # 自绘的图标—文字间距比 Qt 默认宽 2px
        return s

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _fg_color(self) -> QColor:
        skin = self._skin
        if not self.isEnabled():
            return QColor(skin.get("disabled_fg", "#aab1bb"))
        base = QColor(skin["fg"])
        if self.isCheckable() and skin.get("checked_fg"):
            base = motion.mix_color(base, skin["checked_fg"], self._checked_tween.value)
        return motion.mix_color(base, skin["hover_fg"], self._hover.hover)

    # -------------------------------------------------- 绘制

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        skin = self._skin
        hover, press = self._hover.hover, self._hover.press
        checked = self._checked_tween.value if self.isCheckable() else 0.0

        if not self.isEnabled():
            bg = QColor(skin.get("disabled_bg", "#f2f4f7"))
            border = QColor(skin.get("disabled_border", theme.BORDER_SOFT))
            if skin["bg"] == "transparent":
                bg = QColor(Qt.GlobalColor.transparent)
                border = QColor(theme.BORDER_SOFT) if skin["border"] != "transparent" \
                    else QColor(Qt.GlobalColor.transparent)
        else:
            bg = QColor(skin["bg"]) if skin["bg"] != "transparent" else QColor(0, 0, 0, 0)
            border = QColor(skin["border"]) if skin["border"] != "transparent" \
                else QColor(0, 0, 0, 0)
            if skin.get("checked_bg") and checked > 0:
                bg = motion.mix_color(bg, skin["checked_bg"], checked)
                border = motion.mix_color(border, skin.get("checked_border", "transparent"),
                                          checked)
            hover_bg = QColor(skin["hover_bg"]) if skin["hover_bg"] != "transparent" \
                else QColor(0, 0, 0, 0)
            hover_border = QColor(skin["hover_border"]) if skin["hover_border"] != "transparent" \
                else QColor(0, 0, 0, 0)
            if checked <= 0.02 or skin.get("checked_bg") is None:
                bg = motion.mix_color(bg, hover_bg, hover)
                border = motion.mix_color(border, hover_border, hover)
            if press > 0:
                bg = motion.mix_color(bg, skin["press_bg"], press * 0.9)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        lift = skin.get("lift", 0.0) * hover
        if lift:
            rect.translate(0, -lift)
        radius = skin.get("radius", 999)
        r = min(radius, rect.height() / 2) if radius >= 999 else radius
        if skin.get("circular"):
            r = min(rect.width(), rect.height()) / 2

        if self._shadow is not None:
            self._shadow.setEnabled(hover > 0.02 and self.isEnabled())
            self._shadow.setBlurRadius(14.0 * hover)

        p.setPen(Qt.PenStyle.NoPen if border.alpha() == 0 else QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, r, r)

        # ---- 内容（图标 + 文字）
        fg = self._fg_color()
        text = self.text().strip()
        icon_pm: Optional[QPixmap] = None
        if self._icon_name:
            icon_pm = icons.pixmap(self._icon_name, self._icon_px,
                                   self._icon_color or fg.name())
        elif not self.icon().isNull():
            icon_pm = self.icon().pixmap(self.iconSize())

        gap = 6 if (icon_pm is not None and text) else 0
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(text) if text else 0
        icon_w = (icon_pm.width() / icon_pm.devicePixelRatio()) if icon_pm is not None else 0
        icon_h = (icon_pm.height() / icon_pm.devicePixelRatio()) if icon_pm is not None else 0
        total = icon_w + gap + text_w

        pad = skin.get("pad", 10)
        if skin.get("align_left"):
            x = rect.left() + pad
        else:
            x = rect.left() + (rect.width() - total) / 2
        cy = rect.center().y()

        if icon_pm is not None:
            p.drawPixmap(QPointF(x, cy - icon_h / 2), icon_pm)
            x += icon_w + gap
        if text:
            font = QFont(self.font())
            if skin.get("underline"):
                font.setUnderline(self._hover.hover > 0.5)
            p.setFont(font)
            p.setPen(fg)
            avail = rect.right() - pad - x if skin.get("align_left") else text_w + 2
            shown = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(max(10, avail)))
            p.drawText(QRectF(x, rect.top(), max(10.0, avail), rect.height()),
                       int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), shown)
        p.end()


def button(text: str = "", icon_name: str = "", kind: str = "", parent=None,
           on_click: Optional[Callable[[], None]] = None, tooltip: str = "",
           icon_color: Optional[str] = None, icon_size: int = 15) -> QPushButton:
    b = MotionButton(text, kind, parent)
    if icon_name:
        b.set_icon(icon_name, icon_color, icon_size)
    if tooltip:
        b.setToolTip(tooltip)
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


def icon_button(icon_name: str, tooltip: str = "", parent=None,
                on_click: Optional[Callable[[], None]] = None,
                color: str = theme.MUTED, size: int = 16,
                kind: str = "IconBtn") -> QPushButton:
    b = MotionButton("", kind, parent)
    b.set_icon(icon_name, color, size)
    b.setToolTip(tooltip)
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

class Slider(QSlider):
    """对应 HTML 的 `input[type=range]`（4px 轨道 + 16px 白底蓝边滑块）。

    悬停时滑块外扩一圈 `rgba(11,87,208,.10)` 的光环，按下时放大到 1.18 倍，
    都按 `.15s ease` 的进度插值绘制。
    """

    TRACK = 4
    THUMB = 16

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(22)
        self._hover = motion.HoverTracker(self, motion.CONTROL)

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        span = max(1, self.maximum() - self.minimum())
        frac = (self.value() - self.minimum()) / span
        r = self.THUMB / 2
        x0, x1 = rect.left() + r, rect.right() - r
        cx = x0 + (x1 - x0) * frac
        cy = rect.center().y()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e2e5eb"))
        p.drawRoundedRect(QRectF(rect.left(), cy - self.TRACK / 2, rect.width(), self.TRACK), 2, 2)
        p.setBrush(QColor(theme.BLUE if self.isEnabled() else "#a8c0e8"))
        p.drawRoundedRect(QRectF(rect.left(), cy - self.TRACK / 2, cx - rect.left(), self.TRACK),
                          2, 2)

        hover, press = self._hover.hover, self._hover.press
        if hover > 0.01:
            ring = QColor(11, 87, 208)
            ring.setAlphaF(0.10 * hover)
            p.setBrush(ring)
            p.drawEllipse(QPointF(cx, cy), r + 6 * hover, r + 6 * hover)
        scale = 1.0 + 0.18 * press
        p.setPen(QPen(QColor(theme.BLUE if self.isEnabled() else "#a8c0e8"), 2.5))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(cx, cy), (r - 1.25) * scale, (r - 1.25) * scale)
        p.end()

    def mousePressEvent(self, ev) -> None:
        # 点哪跳哪（浏览器里 range 就是这个行为）
        if ev.button() == Qt.MouseButton.LeftButton:
            self._seek(ev.position().x())
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev) -> None:
        if ev.buttons() & Qt.MouseButton.LeftButton:
            self._seek(ev.position().x())
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def _seek(self, x: float) -> None:
        r = self.THUMB / 2
        usable = max(1.0, self.width() - self.THUMB)
        frac = min(1.0, max(0.0, (x - r) / usable))
        self.setValue(round(self.minimum() + frac * (self.maximum() - self.minimum())))


class HoverCard(QFrame):
    """悬停时底色 / 描边渐变的卡片。

    Qt 样式表的 `:hover` 是硬切换，网页版是 `transition: .15s ease`，
    所以这里自绘背景，用 :class:`motion.HoverTracker` 的进度插值。
    """

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None, bg: str = theme.SURFACE,
                 border: str = theme.BORDER, hover_bg: Optional[str] = None,
                 hover_border: Optional[str] = None, radius: int = theme.RADIUS_MD,
                 clickable: bool = False, duration: int = motion.CONTROL):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._bg = QColor(bg) if bg != "transparent" else QColor(0, 0, 0, 0)
        self._border = QColor(border) if border != "transparent" else QColor(0, 0, 0, 0)
        self._hover_bg = QColor(hover_bg) if hover_bg else QColor(self._bg)
        self._hover_border = QColor(hover_border) if hover_border else QColor(self._border)
        self._radius = radius
        self._hover = motion.HoverTracker(self, duration)
        if clickable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._clickable = clickable

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._hover.hover
        bg = motion.mix_color(self._bg, self._hover_bg, t)
        border = motion.mix_color(self._border, self._hover_border, t)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen if border.alpha() == 0 else QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, self._radius, self._radius)
        p.end()

    def mousePressEvent(self, ev) -> None:
        if self._clickable and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)


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
        motion.smooth_scroll(self)          # 滚轮平滑滚动（贴近浏览器手感）

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
