"""角色伤害占比弹窗：环形图 + 明细条（对应 HTML dmgShareModal）。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QToolTip, QWidget

from ...core import state as st
from ...core.constants import ELEM_COLOR_MAP, EXTRA_PALETTE
from ...core.format import dps as fmt_dps, rounded
from .. import icons, motion, theme, widgets as W
from ..session import Session
from ..widgets import hbox, label, vbox
from .base import Modal


def build_share_items(session: Session) -> Dict[str, Any]:
    """与 HTML getDmgShareData() 等价。"""
    cd = session.result
    total = float(cd.get("total", 0.0))
    en = cd.get("en") or session.enabled_chars
    shares = cd.get("shares", {})
    details = cd.get("detailShares", {}) or {}
    direct, feather = details.get("direct", {}) or {}, details.get("feather", {}) or {}

    items: List[Dict[str, Any]] = []
    used = set()
    for idx, c in enumerate(en):
        dmg = float(shares.get(c["id"], 0.0))
        color = ELEM_COLOR_MAP.get(c.get("element"), "#8a7661")
        if color in used:
            color = EXTRA_PALETTE[idx % len(EXTRA_PALETTE)]
        used.add(color)
        items.append({
            "id": c["id"], "name": str(c.get("name", "")), "element": c.get("element"),
            "isReaction": False, "dmg": dmg,
            "pct": (dmg / total * 100) if total > 0 else 0.0, "color": color,
            "direct": float(direct.get(c["id"], 0.0)), "feather": float(feather.get(c["id"], 0.0)),
        })

    rx = float(shares.get("__reaction__", 0.0))
    if rx > 0 or float(details.get("reaction", 0.0)) > 0:
        items.append({
            "id": "__reaction__", "name": "反应", "element": "reaction", "isReaction": True,
            "dmg": rx, "pct": (rx / total * 100) if total > 0 else 0.0,
            "color": theme.REACTION_COLOR, "direct": rx, "feather": 0.0,
        })
    return {"items": items, "total": total, "dps": float(cd.get("dps", 0.0))}


class DonutChart(QWidget):
    """环形占比图，悬停显示明细。"""

    def __init__(self, items: List[Dict[str, Any]], total: float, parent=None, size: int = 250):
        super().__init__(parent)
        self.items = [i for i in items if i["dmg"] > 0]
        self.total = total
        self.setFixedSize(size, size)
        self.setMouseTracking(True)
        self._size = size
        self._hover_idx = -1
        self._fade: Dict[int, motion.Tween] = {}

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = self._size
        pad = 6
        rect = QRectF(pad, pad, s - pad * 2, s - pad * 2)

        if not self.items or self.total <= 0:
            p.setPen(QColor(theme.BORDER))
            p.setBrush(QColor(theme.SURFACE_SUBTLE))
            p.drawEllipse(rect)
        else:
            start = 90 * 16
            for idx, it in enumerate(self.items):
                span = -int(it["dmg"] / self.total * 360 * 16)
                p.setPen(QPen(QColor("#ffffff"), 2))
                # .pie-slice:hover { opacity: .85 }，按 .15s 过渡
                color = QColor(it["color"])
                t = self._fade[idx].value if idx in self._fade else 0.0
                color.setAlphaF(1.0 - 0.15 * t)
                p.setBrush(color)
                p.drawPie(rect, start, span)
                start += span

        inner = rect.adjusted(s * 0.19, s * 0.19, -s * 0.19, -s * 0.19)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SURFACE))
        p.drawEllipse(inner)

        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.ui_font(8.5, QFont.Weight.DemiBold))
        p.drawText(QRectF(inner.left(), inner.center().y() - 22, inner.width(), 18),
                   Qt.AlignmentFlag.AlignCenter, "总期望伤害")
        p.setPen(QColor(theme.TEXT))
        p.setFont(theme.ui_font(12, QFont.Weight.Bold))
        p.drawText(QRectF(inner.left(), inner.center().y() - 4, inner.width(), 24),
                   Qt.AlignmentFlag.AlignCenter, rounded(self.total))
        p.end()

    def _set_hover(self, idx: int) -> None:
        if idx == self._hover_idx:
            return
        for i in (self._hover_idx, idx):
            if i < 0:
                continue
            t = self._fade.get(i)
            if t is None:
                t = motion.Tween(self, lambda _v: self.update(), motion.CONTROL)
                self._fade[i] = t
            t.to(1.0 if i == idx else 0.0)
        self._hover_idx = idx
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if idx >= 0
                               else Qt.CursorShape.ArrowCursor))

    def mouseMoveEvent(self, ev) -> None:
        pos = ev.position()
        c = self._size / 2
        dx, dy = pos.x() - c, pos.y() - c
        dist = math.hypot(dx, dy)
        if not self.items or self.total <= 0 or dist > c - 6 or dist < c * 0.42:
            self._set_hover(-1)
            QToolTip.hideText()
            return
        angle = (math.degrees(math.atan2(-dy, dx)) - 90) % 360
        angle = (360 - angle) % 360
        acc = 0.0
        for idx, it in enumerate(self.items):
            share = it["dmg"] / self.total * 360
            if acc <= angle < acc + share:
                self._set_hover(idx)
                QToolTip.showText(ev.globalPosition().toPoint(),
                                  f"{it['name']}\n{rounded(it['dmg'])} · {it['pct']:.1f}%", self)
                return
            acc += share
        self._set_hover(-1)
        QToolTip.hideText()

    def leaveEvent(self, ev) -> None:
        self._set_hover(-1)
        QToolTip.hideText()
        super().leaveEvent(ev)


class ShareBar(QWidget):
    def __init__(self, item: Dict[str, Any], total: float, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SURFACE_SUBTLE))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 10), 5, 5)
        w = max(0.0, min(100.0, self.item["pct"])) / 100 * self.width()
        if w > 0:
            p.setBrush(QColor(self.item["color"]))
            p.drawRoundedRect(QRectF(0, 0, max(6.0, w), 10), 5, 5)
        p.end()


class DmgShareDialog(Modal):
    def __init__(self, parent, session: Session):
        super().__init__(parent, "角色伤害占比", "pie-chart", width=760, height=620)
        data = build_share_items(session)
        items, total = data["items"], data["total"]
        if not items:
            lb = label("无启用的队伍角色", "Muted")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.add(lb)
            self.finish_body()
            self.add_button("关闭", "", "Primary", self.accept)
            return

        row = hbox(spacing=22)
        left = vbox(spacing=10)
        left.addWidget(DonutChart(items, total, self), 0, Qt.AlignmentFlag.AlignHCenter)

        legend_host = QWidget()
        flow = W.FlowLayout(legend_host, h_spacing=6, v_spacing=5)
        for it in items:
            tag = W.Pill(f"{it['name']} {it['pct']:.1f}%", it["color"])
            flow.addWidget(tag)
        legend_host.setFixedWidth(250)
        left.addWidget(legend_host)

        if session.timeline_on:
            d = label(f"全队 DPS：{fmt_dps(data['dps'])}")
            d.setStyleSheet(f"color:{theme.BLUE};font-size:12.5px;font-weight:700;")
            d.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left.addWidget(d)
        left.addStretch(1)
        row.addLayout(left, 0)

        right = vbox(spacing=9)
        for it in sorted(items, key=lambda x: -x["dmg"]):
            right.addWidget(self._item_card(it, total))
        right.addStretch(1)
        row.addLayout(right, 1)
        self.body.addLayout(row)
        self.finish_body()
        self.add_button("关闭", "", "Primary", self.accept)

    def _item_card(self, it: Dict[str, Any], total: float) -> QWidget:
        card = W.SubCard(padding=12, spacing=7)
        head = hbox(spacing=8)
        ic = QLabel()
        if it["isReaction"]:
            ic.setPixmap(icons.pixmap("zap", 15, theme.REACTION_COLOR))
        else:
            ic.setPixmap(icons.element_pixmap(it["element"], 15))
        head.addWidget(ic)
        nm = label(it["name"])
        nm.setStyleSheet(f"color:{theme.TEXT};font-size:13px;font-weight:700;")
        head.addWidget(nm)
        head.addStretch(1)
        v = label(rounded(it["dmg"]))
        v.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        head.addWidget(v)
        head.addWidget(W.Pill(f"{it['pct']:.1f}%", it["color"]))
        card.add_layout(head)
        card.add(ShareBar(it, total))

        if not it["isReaction"] and it["feather"] > 0:
            if it["direct"] > 0:
                txt = (f"自身直伤 {rounded(it['direct'])}（{it['direct']/total*100:.1f}%）　|　"
                       f"羽毛提供 {rounded(it['feather'])}（{it['feather']/total*100:.1f}%）")
            else:
                txt = f"羽毛提供伤害 {rounded(it['feather'])}（100%）"
            card.add(label(txt, "Muted", wrap=True))
        return card


def open_dmg_share(parent, session: Session) -> None:
    DmgShareDialog(parent, session).exec()
