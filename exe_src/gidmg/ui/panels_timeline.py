"""中央工作区：循环时间轴。

用 QPainter 重绘 HTML 的时间轴视图——刻度尺、每个角色一行、同一行内按占用
情况分轨（lane），瞬发画圆点、持续段画胶囊，跨轴长的区间拆成两段。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from ..core import state as st
from ..core.format import rounded, dps as fmt_dps, trim
from . import icons, theme, widgets as W
from .session import Session
from .widgets import button, hbox, label, vbox

LABEL_W = 132
ROW_PAD = 10
LANE_H = 22
RULER_H = 26


@dataclass
class Block:
    char_id: str
    src_id: str
    title: str
    start: float
    end: float
    lane: int
    color: str
    mode: str
    instant: bool


class TimelineGraph(QWidget):
    """轨道图本体。"""

    jump = Signal(str, str)   # (char_id, source_id)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._rows: List[Tuple[Dict[str, Any], List[Block], int]] = []
        self._hit: List[Tuple[QRect, Block]] = []
        self._ticks = 5

    # ------------------------------------------------------------------ 数据

    def rebuild(self) -> None:
        rot = self.s.rotation
        self._rows = []
        for c in self.s.enabled_chars:
            sources = [d for d in c.get("dmgSrcs", [])
                       if d.get("on") and st.dmg_source_valid(d)]
            if not sources:
                continue
            items: List[Dict[str, Any]] = []
            for d in sources:
                dur = max(0.0, st.numz(d.get("duration")))
                start = ((st.numz(d.get("startTime")) % rot) + rot) % rot
                end = start + dur
                if end <= rot:
                    items.append({"d": d, "s": start, "e": max(start + 0.15, end),
                                  "os": start, "oe": end, "dur": dur})
                else:
                    items.append({"d": d, "s": start, "e": rot, "os": start, "oe": end, "dur": dur})
                    items.append({"d": d, "s": 0.0, "e": end % rot, "os": start, "oe": end, "dur": dur})
            items.sort(key=lambda it: it["s"])

            lane_ends: List[float] = []
            blocks: List[Block] = []
            for it in items:
                lane = next((i for i, last in enumerate(lane_ends) if last <= it["s"] + 0.02), -1)
                if lane < 0:
                    lane = len(lane_ends)
                    lane_ends.append(it["e"])
                else:
                    lane_ends[lane] = it["e"]
                d = it["d"]
                mode = d.get("timingMode") or "instant"
                elem = d.get("element") or c.get("element") or "pyro"
                if it["dur"] == 0:
                    title = f"{c.get('name')} · {d.get('name')} · {trim(it['s'])}s 瞬发"
                else:
                    title = (f"{c.get('name')} · {d.get('name')} · "
                             f"{trim(it['os'])}s–{trim(it['oe'])}s")
                blocks.append(Block(c["id"], d.get("id", ""), title, it["s"], it["e"], lane,
                                    theme.element_color(elem), mode,
                                    it["dur"] == 0 or mode == "instant"))
            self._rows.append((c, blocks, max(1, len(lane_ends))))

        self._ticks = max(4, min(8, round(rot / 4)))
        h = RULER_H + 8
        for _c, _b, lanes in self._rows:
            h += lanes * LANE_H + ROW_PAD * 2
        self.setMinimumHeight(max(120, h + 8))
        self.updateGeometry()
        self.update()

    # ------------------------------------------------------------------ 绘制

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(theme.ui_font(8.5))
        self._hit = []

        rot = self.s.rotation
        track_x = LABEL_W
        track_w = max(40, self.width() - LABEL_W - 4)

        if not self._rows:
            p.setPen(QColor(theme.MUTED_SOFT))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无启用且可结算的伤害来源。")
            p.end()
            return

        # 刻度尺
        y = 4
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRect(0, y, LABEL_W - 12, RULER_H),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "队伍轨迹")
        for i in range(self._ticks + 1):
            x = track_x + track_w * i / self._ticks
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.drawLine(int(x), y + RULER_H - 9, int(x), y + RULER_H - 3)
            p.setPen(QColor(theme.MUTED_SOFT))
            secs = rot * i / self._ticks
            if i == 0:                       # 首个刻度靠左，避免压住「队伍轨迹」
                rect, align = QRect(int(x), y, 44, 12), Qt.AlignmentFlag.AlignLeft
            elif i == self._ticks:           # 末个刻度靠右，避免超出画布
                rect, align = QRect(int(x) - 44, y, 44, 12), Qt.AlignmentFlag.AlignRight
            else:
                rect, align = QRect(int(x) - 22, y, 44, 12), Qt.AlignmentFlag.AlignHCenter
            p.drawText(rect, align | Qt.AlignmentFlag.AlignVCenter, f"{trim(secs)}s")
        y += RULER_H

        for c, blocks, lanes in self._rows:
            row_h = lanes * LANE_H + ROW_PAD * 2
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.SURFACE_SUBTLE))
            p.drawRoundedRect(QRectF(0, y + 2, self.width(), row_h - 4), 12, 12)

            # 角色标签
            badge = icons.element_badge(c.get("element", "pyro"), 24)
            p.drawPixmap(12, int(y + row_h / 2 - 12), badge)
            p.setPen(QColor(theme.TEXT))
            f = theme.ui_font(9, QFont.Weight.DemiBold)
            p.setFont(f)
            p.drawText(QRect(44, int(y + row_h / 2 - 15), LABEL_W - 52, 15),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       str(c.get("name", "")))
            p.setFont(theme.ui_font(8))
            p.setPen(QColor(theme.MUTED_SOFT))
            n_src = len({b.src_id for b in blocks})
            p.drawText(QRect(44, int(y + row_h / 2), LABEL_W - 52, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{n_src} 个来源 · {lanes} 轨")

            # 网格
            p.setPen(QPen(QColor(theme.BORDER), 1, Qt.PenStyle.DotLine))
            for i in range(1, self._ticks):
                x = track_x + track_w * i / self._ticks
                p.drawLine(int(x), int(y + 6), int(x), int(y + row_h - 6))

            for b in blocks:
                lane_y = y + ROW_PAD + b.lane * LANE_H
                x0 = track_x + track_w * (b.start / rot)
                x1 = track_x + track_w * (b.end / rot)
                color = QColor(b.color)
                if b.instant:
                    r = 5
                    rect = QRect(int(x0 - r), int(lane_y + LANE_H / 2 - r), r * 2, r * 2)
                    p.setPen(QPen(QColor("#ffffff"), 1.6))
                    p.setBrush(color)
                    p.drawEllipse(rect)
                    self._hit.append((rect.adjusted(-4, -4, 4, 4), b))
                else:
                    w = max(4.0, x1 - x0)
                    rect = QRectF(x0, lane_y + LANE_H / 2 - 5, w, 10)
                    p.setPen(Qt.PenStyle.NoPen)
                    if b.mode == "uniform_snapshot":
                        fill = QColor(color)
                        fill.setAlpha(210)
                        p.setBrush(fill)
                        p.drawRoundedRect(rect, 5, 5)
                    else:
                        fill = QColor(color)
                        fill.setAlpha(110)
                        p.setBrush(fill)
                        p.drawRoundedRect(rect, 5, 5)
                        p.setPen(QPen(color, 1.4))
                        p.setBrush(Qt.BrushStyle.NoBrush)
                        p.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 5, 5)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(color)
                    p.drawEllipse(QRectF(rect.left() - 1.5, rect.center().y() - 3.5, 7, 7))
                    p.drawEllipse(QRectF(rect.right() - 5.5, rect.center().y() - 3.5, 7, 7))
                    self._hit.append((rect.toRect().adjusted(-2, -6, 2, 6), b))
            y += row_h
        p.end()

    # ------------------------------------------------------------------ 交互

    def _block_at(self, pos: QPoint) -> Optional[Block]:
        for rect, b in reversed(self._hit):
            if rect.contains(pos):
                return b
        return None

    def mouseMoveEvent(self, ev) -> None:
        b = self._block_at(ev.position().toPoint())
        if b:
            QToolTip.showText(ev.globalPosition().toPoint(), b.title, self)
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            QToolTip.hideText()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, ev) -> None:
        b = self._block_at(ev.position().toPoint())
        if b:
            self.jump.emit(b.char_id, b.src_id)
        ev.accept()


class TimelinePanel(QWidget):
    """时间轴工作区（含未开启时的占位态）。"""

    jump = Signal(str, str)
    openSettings = Signal()

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        lay = vbox(self, (0, 0, 0, 0), 0)

        card = W.Card(padding=20, spacing=0)
        lay.addWidget(card)
        lay.addStretch(1)

        card.add(label("ROTATION TIMELINE", "Kicker"))
        card.add(label("循环时间轴", "Heading"))
        card.add(label("查看角色伤害来源在循环内的释放位置与持续区间；点击轨道节点可跳转到对应伤害来源。",
                       "Copy", wrap=True))
        card.body.addSpacing(14)

        # 未开启时间轴
        self.disabled_box = W.SoftCard(padding=18, spacing=12)
        self.disabled_box.add(label("当前未开启循环时间轴模式。开启后即可按出伤时刻与 Buff 覆盖动态结算。",
                                    "Copy", wrap=True))
        btn_row = hbox(spacing=8)
        btn_row.addWidget(button("打开时间轴设置", "settings", "Tonal", self.disabled_box,
                                 self.openSettings.emit))
        btn_row.addStretch(1)
        self.disabled_box.add_layout(btn_row)
        card.add(self.disabled_box)

        # 已开启
        self.container = QWidget()
        cl = vbox(self.container, (0, 0, 0, 0), 12)

        bar = QWidget()
        bl = hbox(bar, (0, 0, 0, 0), 8)
        self.stat_rot = self._stat("轴长", "20s")
        self.stat_total = self._stat("循环总伤", "0")
        self.stat_dps = self._stat("全队秒伤 DPS", "0/s", accent=True)
        for w in (self.stat_rot, self.stat_total, self.stat_dps):
            bl.addWidget(w)
        bl.addStretch(1)
        bl.addWidget(button("轴长设置", "settings-2", "", bar, self.openSettings.emit))
        cl.addWidget(bar)

        self.graph = TimelineGraph(session, self.container)
        self.graph.jump.connect(self.jump.emit)
        cl.addWidget(self.graph)
        card.add(self.container)

        session.calcFinished.connect(self.refresh)
        self.refresh()

    def _stat(self, name: str, value: str, accent: bool = False) -> QWidget:
        w = W.SoftCard(padding=10, spacing=2)
        w.setMinimumWidth(112)
        w.add(label(name, "Muted"))
        v = label(value)
        v.setStyleSheet(f"color:{theme.BLUE if accent else theme.TEXT};"
                        f"font-size:14px;font-weight:700;")
        w.add(v)
        setattr(w, "value_label", v)
        return w

    def refresh(self) -> None:
        on = self.s.timeline_on
        self.disabled_box.setVisible(not on)
        self.container.setVisible(on)
        if not on:
            return
        res = self.s.result
        self.stat_rot.value_label.setText(f"{trim(self.s.rotation)}s")
        self.stat_total.value_label.setText(rounded(res.get("total", 0)))
        self.stat_dps.value_label.setText(fmt_dps(res.get("dps", 0)))
        if self.isVisible():
            self.graph.rebuild()

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if self.s.timeline_on:
            self.graph.rebuild()
