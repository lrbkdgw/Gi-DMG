"""动效工具：把 HTML 版的 CSS transition 映射到 Qt。

网页版的手感几乎全部来自 style2.css 里的过渡，主要有这些：

==============================  ==========================================
CSS 选择器                      过渡
==============================  ==========================================
``.pi`` / ``input``             ``border-color .16s, background .16s, box-shadow .16s``
``.sidebar-entry``              ``background .15s, color .15s, border-color .15s``
``.sidebar-character-row``      ``background-color .15s, color .15s``
``.bs`` / ``.bg`` / ``.chip``   ``.15s ease``（``.bg:hover`` 还会 ``translateY(-1px)``）
``.tgl``                        ``background-color .2s``；``.tgl span`` ``transform .2s``
``.studio-select-trigger``      ``.16s``；箭头 ``transform .16s``
``.timeline-character-row``     ``background-color .15s``
``.pie-slice`` / ``.pie-tooltip`` ``opacity .15s`` / ``opacity .1s``
==============================  ==========================================

Qt Widgets 没有样式过渡，所以这里提供统一的补间工具：

* :class:`HoverTracker` —— 跟踪 hover / pressed / checked 三个 0~1 的进度值，
  控件在 ``paintEvent`` 里按进度插值颜色，就得到了和 CSS 一样的淡入淡出；
* :func:`focus_glow` —— 用阴影特效模拟 ``box-shadow: 0 0 0 3px rgba(11,87,208,.12)``；
* :func:`fade_in` / :func:`pop_in` —— 弹窗与面板出现时的淡入；
* :class:`SmoothScroll` —— 滚轮平滑滚动，接近浏览器的滚动手感；
* :class:`Scrim` —— 弹窗背后的遮罩，对应 ``.modal-overlay`` 的半透明背景。
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QEvent, QObject, QPoint,
                            QPropertyAnimation, Qt, QVariantAnimation)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractScrollArea, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QWidget)

# ------------------------------------------------------------------ 时长 / 缓动

FAST = 120        # .12s —— contrib chip
BASE = 150        # .15s —— 绝大多数 hover
CONTROL = 160     # .16s —— 输入框 / 下拉触发器
SLOW = 200        # .20s —— 开关
PANEL = 190       # 工作区切换、弹窗淡入

EASE = QEasingCurve.Type.OutCubic
EASE_INOUT = QEasingCurve.Type.InOutCubic


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_color(a: str | QColor, b: str | QColor, t: float) -> QColor:
    """按 t(0~1) 在两个颜色之间插值，含 alpha。"""
    ca = QColor(a) if not isinstance(a, QColor) else a
    cb = QColor(b) if not isinstance(b, QColor) else b
    t = max(0.0, min(1.0, t))
    return QColor(
        round(lerp(ca.red(), cb.red(), t)),
        round(lerp(ca.green(), cb.green(), t)),
        round(lerp(ca.blue(), cb.blue(), t)),
        round(lerp(ca.alpha(), cb.alpha(), t)),
    )


# ------------------------------------------------------------------ 进度补间

class Tween(QVariantAnimation):
    """0~1 的进度补间，每帧回调一次。"""

    def __init__(self, parent: QObject, on_tick: Callable[[float], None],
                 duration: int = BASE, easing: QEasingCurve.Type = EASE):
        super().__init__(parent)
        self.setStartValue(0.0)
        self.setEndValue(0.0)
        self.setDuration(duration)
        self.setEasingCurve(easing)
        self._value = 0.0
        self._on_tick = on_tick
        self.valueChanged.connect(self._tick)

    def _tick(self, value) -> None:
        self._value = float(value)
        self._on_tick(self._value)

    @property
    def value(self) -> float:
        return self._value

    def to(self, target: float, animate: bool = True) -> None:
        target = max(0.0, min(1.0, float(target)))
        if abs(target - self._value) < 1e-3:
            self.stop()
            self._value = target
            return
        self.stop()
        if not animate:
            self._value = target
            self._on_tick(target)
            return
        self.setStartValue(self._value)
        self.setEndValue(target)
        self.start()


class HoverTracker(QObject):
    """给任意控件加上「悬停 / 按下」的动画进度。

    控件在 paintEvent 里读 :attr:`hover` 与 :attr:`press`（都是 0~1），
    按进度插值颜色即可复刻 CSS 的 ``transition: background .15s ease``。
    """

    def __init__(self, widget: QWidget, duration: int = BASE,
                 on_change: Optional[Callable[[], None]] = None,
                 press_duration: int = 90):
        super().__init__(widget)
        self._widget = widget
        self._on_change = on_change or widget.update
        self._hover = Tween(self, lambda _v: self._on_change(), duration)
        self._press = Tween(self, lambda _v: self._on_change(), press_duration)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        widget.installEventFilter(self)

    # -------------------------------------------------- 状态

    @property
    def hover(self) -> float:
        return self._hover.value if self._widget.isEnabled() else 0.0

    @property
    def press(self) -> float:
        return self._press.value if self._widget.isEnabled() else 0.0

    def reset(self) -> None:
        self._hover.to(0.0, animate=False)
        self._press.to(0.0, animate=False)

    # -------------------------------------------------- 事件

    def eventFilter(self, obj, ev) -> bool:
        if obj is self._widget:
            t = ev.type()
            if t in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
                self._hover.to(1.0)
            elif t in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self._hover.to(0.0)
                self._press.to(0.0)
            elif t == QEvent.Type.MouseButtonPress:
                self._press.to(1.0)
            elif t in (QEvent.Type.MouseButtonRelease, QEvent.Type.FocusOut):
                self._press.to(0.0)
            elif t == QEvent.Type.EnabledChange and not self._widget.isEnabled():
                self.reset()
        return False


# ------------------------------------------------------------------ 焦点光晕

class _FocusGlow(QObject):
    """``.pi:focus`` 的 ``box-shadow: 0 0 0 3px rgba(11,87,208,.12)``。

    Qt 的样式表画不出外发光，这里用一个 blur 很小的阴影特效模拟，
    并在获得 / 失去焦点时补间 blur 半径，得到 .16s 的淡入淡出。
    """

    def __init__(self, widget: QWidget, color: str, radius: float = 9.0):
        super().__init__(widget)
        self._widget = widget
        self._color = QColor(color)
        self._radius = radius
        self._effect: Optional[QGraphicsDropShadowEffect] = None
        self._tween = Tween(self, self._apply, CONTROL)
        widget.installEventFilter(self)

    def _ensure_effect(self) -> QGraphicsDropShadowEffect:
        if self._effect is None or self._widget.graphicsEffect() is not self._effect:
            self._effect = QGraphicsDropShadowEffect(self._widget)
            self._effect.setOffset(0, 0)
            self._effect.setBlurRadius(0.0)
            self._widget.setGraphicsEffect(self._effect)
        return self._effect

    def _apply(self, t: float) -> None:
        if t <= 0.001:
            if self._effect is not None:
                self._effect.setEnabled(False)
            return
        eff = self._ensure_effect()
        eff.setEnabled(True)
        col = QColor(self._color)
        col.setAlphaF(min(1.0, self._color.alphaF() * t))
        eff.setColor(col)
        eff.setBlurRadius(self._radius * t)

    def eventFilter(self, obj, ev) -> bool:
        if obj is self._widget:
            if ev.type() == QEvent.Type.FocusIn:
                self._tween.to(1.0)
            elif ev.type() == QEvent.Type.FocusOut:
                self._tween.to(0.0)
        return False


def focus_glow(widget: QWidget, color: str = "rgba(11,87,208,0.38)",
               radius: float = 9.0) -> QWidget:
    """给输入类控件加上聚焦光晕（对应 HTML 的聚焦 box-shadow）。"""
    if isinstance(color, str) and color.startswith("rgba"):
        nums = color[color.index("(") + 1:color.rindex(")")].split(",")
        c = QColor(int(nums[0]), int(nums[1]), int(nums[2]))
        c.setAlphaF(float(nums[3]))
    else:
        c = QColor(color)
    if getattr(widget, "_focus_glow", None) is None:
        setattr(widget, "_focus_glow", _FocusGlow(widget, c, radius))
    return widget


# ------------------------------------------------------------------ 淡入 / 弹出

def fade_in(widget: QWidget, duration: int = PANEL, start: float = 0.0,
            on_done: Optional[Callable[[], None]] = None) -> Optional[QPropertyAnimation]:
    """淡入一个控件（用 QGraphicsOpacityEffect，不影响布局）。"""
    if widget.graphicsEffect() is not None and not isinstance(
            widget.graphicsEffect(), QGraphicsOpacityEffect):
        if on_done:
            on_done()
        return None
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
    eff.setEnabled(True)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setEasingCurve(EASE)
    anim.setStartValue(start)
    anim.setEndValue(1.0)

    def _finish() -> None:
        eff.setEnabled(False)          # 画完就摘掉，避免持续的离屏合成开销
        if on_done:
            on_done()

    anim.finished.connect(_finish)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    setattr(widget, "_fade_anim", anim)
    return anim


def window_fade_in(window: QWidget, duration: int = 140,
                   start: float = 0.0, rise: int = 8) -> None:
    """弹窗出现：窗口透明度淡入 + 轻微上浮（对应网页弹窗的出现感）。"""
    window.setWindowOpacity(start)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setEasingCurve(EASE)
    anim.setStartValue(start)
    anim.setEndValue(1.0)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    setattr(window, "_fade_anim", anim)

    if rise:
        geo = window.geometry()
        window.move(geo.x(), geo.y() + rise)
        move = QPropertyAnimation(window, b"pos", window)
        move.setDuration(duration + 40)
        move.setEasingCurve(EASE)
        move.setStartValue(QPoint(geo.x(), geo.y() + rise))
        move.setEndValue(QPoint(geo.x(), geo.y()))
        move.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        setattr(window, "_rise_anim", move)


# ------------------------------------------------------------------ 平滑滚动

class SmoothScroll(QObject):
    """滚轮平滑滚动：把一次滚轮事件摊到若干帧里，接近浏览器的滚动手感。"""

    def __init__(self, area: QAbstractScrollArea, step: int = 120, duration: int = 240):
        super().__init__(area)
        self._area = area
        self._step = step
        self._anim = QPropertyAnimation(area.verticalScrollBar(), b"value", self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        area.viewport().installEventFilter(self)
        area.installEventFilter(self)

    def eventFilter(self, obj, ev) -> bool:
        if ev.type() != QEvent.Type.Wheel:
            return False
        bar = self._area.verticalScrollBar()
        if bar is None or bar.maximum() == 0:
            return False
        if ev.modifiers() & (Qt.KeyboardModifier.ControlModifier
                             | Qt.KeyboardModifier.ShiftModifier):
            return False
        delta = ev.angleDelta().y()
        if not delta:
            return False
        running = self._anim.state() == QAbstractAnimation.State.Running
        current = self._anim.endValue() if running else bar.value()
        target = int(current) - int(delta / 120 * self._step)
        target = max(bar.minimum(), min(bar.maximum(), target))
        if target == bar.value() and not running:
            return False
        self._anim.stop()
        self._anim.setStartValue(bar.value())
        self._anim.setEndValue(target)
        self._anim.start()
        ev.accept()
        return True


def smooth_scroll(area: QAbstractScrollArea, step: int = 120) -> QAbstractScrollArea:
    if getattr(area, "_smooth_scroll", None) is None:
        setattr(area, "_smooth_scroll", SmoothScroll(area, step))
    return area


# ------------------------------------------------------------------ 遮罩

class Scrim(QWidget):
    """弹窗背后的半透明遮罩，对应 ``.modal-overlay``（rgba(24,34,51,.38)）。"""

    def __init__(self, parent: QWidget, color: str = "#182233", alpha: float = 0.38):
        super().__init__(parent)
        self._color = QColor(color)
        self._max_alpha = alpha
        self._alpha = 0.0
        self._depth = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()
        self._tween = Tween(self, self._set_alpha, PANEL, EASE)
        parent.installEventFilter(self)

    @classmethod
    def of(cls, host: QWidget) -> "Scrim":
        """取（或创建）某个窗口上的遮罩，同一窗口共用一层。"""
        existing = getattr(host, "_gidmg_scrim", None)
        if isinstance(existing, cls):
            return existing
        scrim = cls(host)
        setattr(host, "_gidmg_scrim", scrim)
        return scrim

    def _set_alpha(self, t: float) -> None:
        self._alpha = t * self._max_alpha
        if t <= 0.002 and self._depth == 0:
            self.hide()
        self.update()

    def push(self) -> None:
        """打开一个弹窗。"""
        self._depth += 1
        if self._depth == 1:
            self.setGeometry(self.parentWidget().rect())
            self.show()
            self.raise_()
            self._tween.to(1.0)

    def pop(self) -> None:
        self._depth = max(0, self._depth - 1)
        if self._depth == 0:
            self._tween.to(0.0)

    def eventFilter(self, obj, ev) -> bool:
        if obj is self.parentWidget() and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def paintEvent(self, _ev) -> None:
        if self._alpha <= 0.002:
            return
        p = QPainter(self)
        col = QColor(self._color)
        col.setAlphaF(self._alpha)
        p.fillRect(self.rect(), col)
        p.end()


# ------------------------------------------------------------------ 工作区切换

class StackFader(QObject):
    """QStackedWidget 换页时给新页面加一点淡入 + 上浮。

    HTML 是直接 toggle `hidden`，但网页里滚动位置复位 + 重排本身就有视觉缓冲；
    Qt 里直接换页会很「硬」，所以补一段 190ms 的淡入，观感与网页接近。
    """

    def __init__(self, stack, duration: int = PANEL):
        super().__init__(stack)
        self._stack = stack
        self._duration = duration

    def switch(self, index: int) -> None:
        if index == self._stack.currentIndex():
            return
        self._stack.setCurrentIndex(index)
        page = self._stack.currentWidget()
        if page is not None:
            fade_in(page, self._duration, 0.15)
