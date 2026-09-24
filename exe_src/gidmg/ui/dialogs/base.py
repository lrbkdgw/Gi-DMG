"""弹窗基类：与 HTML `.modal-overlay` 一致的白底圆角卡片 + 标题栏。

网页版的弹窗是一层 `rgba(24,34,51,.38)` 的遮罩加一张 24px 圆角、带
`--studio-shadow-float` 投影的白卡片，出现时淡入。Qt 的系统对话框既没有圆角也没有
遮罩，所以这里把窗口设成无边框 + 透明背景，自己画卡片与阴影：

* 主窗口上盖一层 :class:`motion.Scrim` 遮罩（淡入淡出）；
* 弹窗整体淡入并上浮 8px（``motion.window_fade_in``）；
* 标题栏可拖动，Esc / 关闭按钮照旧；
* 打开后自动把焦点落到第一个输入控件（对应 HTML 的 `requestAnimationFrame` 聚焦）。

子类的用法保持不变：往 ``self.body`` 里塞内容，往 ``self.footer`` 里塞按钮。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox, QDialog, QFrame,
                               QGraphicsDropShadowEffect, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QTextEdit, QWidget)

from .. import icons, motion, theme, widgets as W
from ..widgets import hbox, icon_button, label, vbox

MARGIN = 18          # 给投影留出的透明外边距
RADIUS = theme.RADIUS_CARD


class Modal(QDialog):
    """统一外观的弹窗。

    子类往 self.body 里塞内容，往 self.footer 里塞按钮。
    """

    def __init__(self, parent: Optional[QWidget] = None, title: str = "", icon_name: str = "",
                 width: int = 560, height: Optional[int] = None, badge: str = ""):
        super().__init__(parent)
        self.setObjectName("Modal")
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(width + MARGIN * 2,
                    (height or min(760, max(320, int(width * 0.9)))) + MARGIN * 2)

        self._drag_at: Optional[QPoint] = None
        self._scrim: Optional[motion.Scrim] = None

        outer = vbox(self, (MARGIN, MARGIN, MARGIN, MARGIN), 0)

        # ---------------- 卡片（圆角 + 浮动阴影）
        self.card = QFrame(self)
        self.card.setObjectName("ModalCard")
        glow = QGraphicsDropShadowEffect(self.card)
        glow.setBlurRadius(46)                      # 0 12px 36px rgba(24,37,59,.14)
        glow.setOffset(0, 12)
        glow.setColor(theme.tint("#18253b", 46))
        self.card.setGraphicsEffect(glow)
        outer.addWidget(self.card)
        root = vbox(self.card, (0, 0, 0, 0), 0)

        # ---------------- 标题栏
        head = _DragBar(self)
        head.setObjectName("ModalHead")
        head.setStyleSheet(f"QWidget#ModalHead {{ background:transparent; "
                           f"border-bottom:1px solid {theme.BORDER}; }}")
        hl = hbox(head, (20, 14, 14, 14), 9)
        if icon_name:
            ic = QLabel()
            ic.setPixmap(icons.pixmap(icon_name, 17, theme.BLUE))
            hl.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        self.title_label = label(title)
        self.title_label.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;"
                                       "background:transparent;")
        hl.addWidget(self.title_label)
        if badge:
            hl.addWidget(W.Pill(badge, theme.MUTED))
        hl.addStretch(1)
        self.head_extra = hbox(spacing=6)
        hl.addLayout(self.head_extra)
        hl.addWidget(icon_button("x", "关闭", head, self.reject, size=16))
        root.addWidget(head)
        self.head = head

        # ---------------- 内容
        self.scroll = W.ScrollArea(margins=(20, 16, 20, 16), spacing=12)
        root.addWidget(self.scroll, 1)
        self.body = self.scroll.body

        # ---------------- 底部
        self.foot = QWidget()
        self.foot.setObjectName("ModalFoot")
        self.foot.setStyleSheet(f"QWidget#ModalFoot {{ background:transparent; "
                                f"border-top:1px solid {theme.BORDER}; }}")
        self.footer = hbox(self.foot, (16, 12, 16, 12), 8)
        self.footer.addStretch(1)
        self.foot.setVisible(False)
        root.addWidget(self.foot)

    # ------------------------------------------------------------------ 内容 API

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)
        self.setWindowTitle(text)

    def add_head(self, w: QWidget) -> QWidget:
        """往标题栏右侧塞一个控件（关闭按钮之前）。"""
        self.head_extra.addWidget(w)
        return w

    def add(self, w: QWidget, stretch: int = 0) -> QWidget:
        self.body.addWidget(w, stretch)
        return w

    def add_button(self, text: str, icon_name: str = "", kind: str = "", on_click=None):
        self.foot.setVisible(True)
        b = W.button(text, icon_name, kind, self.foot, on_click)
        self.footer.addWidget(b)
        return b

    def finish_body(self) -> None:
        self.body.addStretch(1)

    # ------------------------------------------------------------------ 出场 / 退场

    def _host(self) -> Optional[QWidget]:
        win = self.parentWidget().window() if self.parentWidget() is not None else None
        return win if isinstance(win, QWidget) else None

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if not ev.spontaneous():
            host = self._host()
            if host is not None and self._scrim is None:
                self._scrim = motion.Scrim.of(host)
            if self._scrim is not None:
                self._scrim.push()
            self._center_on_host()
            motion.window_fade_in(self)
            QTimer.singleShot(0, self._focus_first)

    def _center_on_host(self) -> None:
        host = self._host()
        if host is None or not host.isVisible():
            return
        geo = host.frameGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  max(geo.top(), geo.center().y() - self.height() // 2))

    def _focus_first(self) -> None:
        """对应 HTML `toggleModal` 里的自动聚焦首个可交互控件。"""
        types = (QLineEdit, QAbstractSpinBox, QComboBox, QPlainTextEdit, QTextEdit)
        for w in self.scroll.inner.findChildren(QWidget):
            if isinstance(w, types) and w.isEnabled() and w.isVisibleTo(self) \
                    and w.focusPolicy() != Qt.FocusPolicy.NoFocus:
                w.setFocus(Qt.FocusReason.OtherFocusReason)
                return
        for b in self.findChildren(QPushButton):
            if b.isEnabled() and b.isVisibleTo(self) and b.parent() is not self.head:
                b.setFocus(Qt.FocusReason.OtherFocusReason)
                return

    def _release_scrim(self) -> None:
        if self._scrim is not None:
            self._scrim.pop()
            self._scrim = None

    def hideEvent(self, ev) -> None:
        self._release_scrim()
        super().hideEvent(ev)

    def closeEvent(self, ev) -> None:
        self._release_scrim()
        super().closeEvent(ev)

    def done(self, result: int) -> None:
        self._release_scrim()
        super().done(result)

    # ------------------------------------------------------------------ 拖动

    def start_drag(self, global_pos: QPoint) -> None:
        self._drag_at = global_pos - self.frameGeometry().topLeft()

    def drag_to(self, global_pos: QPoint) -> None:
        if self._drag_at is not None:
            self.move(global_pos - self._drag_at)

    def end_drag(self) -> None:
        self._drag_at = None


class _DragBar(QWidget):
    """弹窗标题栏：按住可拖动整个窗口（无边框窗口自己实现）。"""

    def __init__(self, modal: Modal):
        super().__init__(modal.card)
        self._modal = modal

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._modal.start_drag(ev.globalPosition().toPoint())
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev) -> None:
        if ev.buttons() & Qt.MouseButton.LeftButton:
            self._modal.drag_to(ev.globalPosition().toPoint())
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev) -> None:
        self._modal.end_drag()
        super().mouseReleaseEvent(ev)
