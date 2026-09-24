"""弹窗基类：与 HTML .modal-overlay 一致的白底圆角卡片 + 标题栏。"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QSizePolicy,
                               QVBoxLayout, QWidget)

from .. import icons, theme, widgets as W
from ..widgets import hbox, icon_button, label, vbox


class Modal(QDialog):
    """统一外观的弹窗。

    子类往 self.body 里塞内容，往 self.footer 里塞按钮。
    """

    def __init__(self, parent: Optional[QWidget] = None, title: str = "", icon_name: str = "",
                 width: int = 560, height: Optional[int] = None, badge: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(width, height or min(760, max(320, int(width * 0.9))))
        self.setStyleSheet(f"QDialog {{ background:{theme.SURFACE}; }}")

        root = vbox(self, (0, 0, 0, 0), 0)

        # ---------------- 标题栏
        head = QWidget()
        head.setObjectName("ModalHead")
        head.setStyleSheet(f"QWidget#ModalHead {{ background:{theme.SURFACE}; "
                           f"border-bottom:1px solid {theme.BORDER}; }}")
        hl = hbox(head, (20, 14, 14, 14), 9)
        if icon_name:
            ic = QLabel()
            ic.setPixmap(icons.pixmap(icon_name, 17, theme.BLUE))
            hl.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        self.title_label = label(title)
        self.title_label.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;")
        hl.addWidget(self.title_label)
        if badge:
            hl.addWidget(W.Pill(badge, theme.MUTED))
        hl.addStretch(1)
        self.head_extra = hbox(spacing=6)
        hl.addLayout(self.head_extra)
        hl.addWidget(icon_button("x", "关闭", head, self.reject, size=16))
        root.addWidget(head)

        # ---------------- 内容
        self.scroll = W.ScrollArea(margins=(20, 16, 20, 16), spacing=12)
        root.addWidget(self.scroll, 1)
        self.body = self.scroll.body

        # ---------------- 底部
        self.foot = QWidget()
        self.foot.setObjectName("ModalFoot")
        self.foot.setStyleSheet(f"QWidget#ModalFoot {{ background:{theme.SURFACE}; "
                                f"border-top:1px solid {theme.BORDER}; }}")
        self.footer = hbox(self.foot, (16, 12, 16, 12), 8)
        self.footer.addStretch(1)
        self.foot.setVisible(False)
        root.addWidget(self.foot)

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
