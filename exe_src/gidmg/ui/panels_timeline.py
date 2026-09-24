"""中央工作区：循环时间轴。

用 QPainter 重绘 HTML 的时间轴视图——刻度尺、每个角色一行、同一行内按占用
情况分轨（lane），瞬发画圆点、持续段画胶囊，跨轴长的区间拆成两段。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from ..core import state as st
from ..core.format import rounded, dps as fmt_dps, trim
from . import icons, motion, theme, widgets as W
from .session import Session
from .widgets import button, hbox, label, vbox

# 几何全部对齐 HTML 的 .timeline-* 规则（style2.css 最终层叠结果）
LABEL_W = 150            # grid-template-columns: 150px minmax(0,1fr)
RULER_H = 38             # .timeline-ruler-row { min-height: 38px }
LANE_H = 26              # .timeline-lane { height: 26px }
LANE_GAP = 4             # .timeline-lane + .timeline-lane { margin-top: 4px }
LANES_PAD = 8            # .timeline-lanes { padding: 8px 0 }
ROW_MIN_H = 46           # 标签列 10px 内边距 + 26px 徽标
BOARD_RADIUS = 18        # .timeline-board { border-radius: 18px }
GRID_LINE = "#eceff4"    # .timeline-lane 竖向网格
LANE_MID = "#f1f4f9"     # .timeline-lane::before
TICK_COLOR = "#cdd3db"   # .timeline-tick i
ROW_HOVER = "#fafbfd"    # .timeline-character-row:hover
CAP_FILL = "#fbfbfd"     # .tl-cap / .timeline-instant 内部填色


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
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._rows: List[Tuple[Dict[str, Any], List[Block], int]] = []
        self._hit: List[Tuple[QRect, Block]] = []
        self._row_rects: List[QRect] = []
        self._hover_row = -1
        self._row_t: Dict[int, motion.Tween] = {}
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
        self._hover_row = -1
        self._row_t.clear()
        h = RULER_H
        for _c, _b, lanes in self._rows:
            h += self._row_height(lanes)
        self.setMinimumHeight(max(120, h + 2))
        self.updateGeometry()
        self.update()

    @staticmethod
    def _row_height(lanes: int) -> int:
        return max(ROW_MIN_H, LANES_PAD * 2 + lanes * LANE_H + (lanes - 1) * LANE_GAP)

    def _row_progress(self, index: int) -> float:
        t = self._row_t.get(index)
        return t.value if t is not None else 0.0

    # ------------------------------------------------------------------ 绘制

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._hit = []
        self._row_rects = []

        rot = self.s.rotation
        board = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # ---- 空态：.timeline-empty-state（浅灰圆角块，无边框）
        if not self._rows:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.SURFACE_SUBTLE))
            p.drawRoundedRect(board, BOARD_RADIUS, BOARD_RADIUS)
            p.setPen(QColor(theme.MUTED))
            p.setFont(theme.ui_font(9))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无启用且可结算的伤害来源。")
            p.end()
            return

        # ---- 板面：白底 + 1px 边框 + 18px 圆角，内容按圆角裁剪
        path = QPainterPath()
        path.addRoundedRect(board, BOARD_RADIUS, BOARD_RADIUS)
        p.save()
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.SURFACE))
        p.drawPath(path)

        track_x = LABEL_W
        track_w = max(40.0, board.width() - LABEL_W)
        step = track_w / self._ticks

        # ---- 刻度行
        p.setBrush(QColor(theme.SURFACE_SUBTLE))
        p.drawRect(QRectF(0, 0, board.right(), RULER_H))
        p.setPen(QColor(theme.MUTED))
        f = theme.ui_font(7.5, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 106)
        p.setFont(f)
        p.drawText(QRectF(16, 0, LABEL_W - 24, RULER_H),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "队伍轨迹")
        # 竖线只画 6px 短标记，首尾不画（与 :first-child / :last-child i{display:none} 一致）
        p.setPen(QPen(QColor(TICK_COLOR), 1))
        for i in range(1, self._ticks):
            x = round(track_x + step * i) + 0.5
            p.drawLine(QPointF(x, RULER_H / 2 - 3), QPointF(x, RULER_H / 2 + 3))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawLine(QPointF(0, RULER_H - 0.5), QPointF(board.right(), RULER_H - 0.5))

        y = float(RULER_H)
        for index, (c, blocks, lanes) in enumerate(self._rows):
            row_h = self._row_height(lanes)
            row_rect = QRectF(0, y, board.right(), row_h)
            self._row_rects.append(row_rect.toRect())

            hover = self._row_progress(index)
            if hover > 0.001:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(motion.mix_color(theme.SURFACE, ROW_HOVER, hover))
                p.drawRect(row_rect)

            # 标签列
            pm = icons.element_pixmap(c.get("element", "pyro"), 17)
            p.drawPixmap(QPointF(14 + (26 - 17) / 2, y + row_h / 2 - 8.5), pm)
            tx = 14 + 26 + 9
            p.setPen(QColor(theme.TEXT))
            p.setFont(theme.ui_font(9, QFont.Weight.DemiBold))
            p.drawText(QRectF(tx, y + row_h / 2 - 15, LABEL_W - tx - 12, 15),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom),
                       str(c.get("name", "")))
            p.setFont(theme.ui_font(7.5))
            p.setPen(QColor("#9aa1ab"))
            n_src = len({b.src_id for b in blocks})
            p.drawText(QRectF(tx, y + row_h / 2 + 1, LABEL_W - tx - 12, 14),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                       f"{n_src} 个来源 · {lanes} 轨")
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.drawLine(QPointF(LABEL_W - 0.5, y), QPointF(LABEL_W - 0.5, y + row_h))

            # 轨道区
            lanes_top = y + (row_h - (lanes * LANE_H + (lanes - 1) * LANE_GAP)) / 2
            for lane in range(lanes):
                ly = lanes_top + lane * (LANE_H + LANE_GAP)
                # 竖向网格（每个刻度一条 1px 线）
                p.setPen(QPen(QColor(GRID_LINE), 1))
                for i in range(self._ticks):
                    x = round(track_x + step * i) + 0.5
                    p.drawLine(QPointF(x, ly), QPointF(x, ly + LANE_H))
                # 轨道中线 2px
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(LANE_MID))
                p.drawRoundedRect(QRectF(track_x, ly + LANE_H / 2 - 1, track_w, 2), 1, 1)

            for b in blocks:
                ly = lanes_top + b.lane * (LANE_H + LANE_GAP)
                cy = ly + LANE_H / 2
                x0 = track_x + track_w * (b.start / rot)
                x1 = track_x + track_w * (b.end / rot)
                color = QColor(b.color)
                if b.instant:
                    # .timeline-instant：16px 圆环，2.5px 描边，圆心对齐时间点
                    p.setPen(QPen(color, 2.5))
                    p.setBrush(QColor(CAP_FILL))
                    p.drawEllipse(QPointF(x0, cy), 6.75, 6.75)
                    self._hit.append((QRect(int(x0 - 10), int(cy - 10), 20, 20), b))
                else:
                    w = max(8.0, x1 - x0)
                    # .tl-line：4px 色条；dynamic 为白底 + 1px 内描边
                    p.setPen(Qt.PenStyle.NoPen)
                    if b.mode == "uniform_snapshot":
                        p.setBrush(color)
                        p.drawRoundedRect(QRectF(x0, cy - 2, w, 4), 2, 2)
                    else:
                        p.setBrush(QColor("#ffffff"))
                        p.drawRoundedRect(QRectF(x0, cy - 2, w, 4), 2, 2)
                        p.setPen(QPen(color, 1))
                        p.setBrush(Qt.BrushStyle.NoBrush)
                        p.drawRoundedRect(QRectF(x0 + 0.5, cy - 1.5, w - 1, 3), 1.5, 1.5)
                    # .tl-cap：两端 12px 圆帽，2px 描边
                    p.setPen(QPen(color, 2))
                    p.setBrush(QColor(CAP_FILL))
                    p.drawEllipse(QPointF(x0, cy), 5, 5)
                    p.drawEllipse(QPointF(x0 + w, cy), 5, 5)
                    self._hit.append((QRect(int(x0 - 6), int(cy - 8), int(w + 12), 16), b))

            y += row_h
            if index < len(self._rows) - 1:
                p.setPen(QPen(QColor(theme.BORDER), 1))
                p.drawLine(QPointF(0, y - 0.5), QPointF(board.right(), y - 0.5))

        p.restore()
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    # ------------------------------------------------------------------ 交互

    def _block_at(self, pos: QPoint) -> Optional[Block]:
        for rect, b in reversed(self._hit):
            if rect.contains(pos):
                return b
        return None

    def _set_hover_row(self, index: int) -> None:
        if index == self._hover_row:
            return
        for i in (self._hover_row, index):
            if i < 0:
                continue
            t = self._row_t.get(i)
            if t is None:
                t = motion.Tween(self, lambda _v: self.update(), motion.CONTROL)
                self._row_t[i] = t
            t.to(1.0 if i == index else 0.0)
        self._hover_row = index

    def mouseMoveEvent(self, ev) -> None:
        pos = ev.position().toPoint()
        b = self._block_at(pos)
        row = next((i for i, r in enumerate(self._row_rects) if r.contains(pos)), -1)
        self._set_hover_row(row)
        if b:
            QToolTip.showText(ev.globalPosition().toPoint(), b.title, self)
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            QToolTip.hideText()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def leaveEvent(self, ev) -> None:
        self._set_hover_row(-1)
        super().leaveEvent(ev)

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
        settings_btn = button("轴长设置", "settings-2", "", bar, self.openSettings.emit)
        settings_btn.setMinimumHeight(34)          # .timeline-settings-btn
        bl.addWidget(settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(bar)

        self.graph = TimelineGraph(session, self.container)
        self.graph.jump.connect(self.jump.emit)
        cl.addWidget(self.graph)
        card.add(self.container)

        session.calcFinished.connect(self.refresh)
        self.refresh()

    def _stat(self, name: str, value: str, accent: bool = False) -> QWidget:
        """对应 HTML 的 .timeline-stat（96px 起宽、8/14 内边距、14px 圆角）。"""
        w = W.SoftCard(padding=0, spacing=2)
        w.body.setContentsMargins(14, 8, 14, 8)
        w.setMinimumWidth(96)
        w.setStyleSheet(
            f"QFrame#SoftCard {{ background:{theme.BLUE_TINT if accent else theme.SURFACE_SUBTLE};"
            f"border:1px solid transparent; border-radius:14px; }}")
        cap = label(name)
        cap.setStyleSheet(f"color:{'#5581ce' if accent else theme.MUTED};"
                          "font-size:10px;font-weight:600;background:transparent;")
        w.add(cap)
        v = label(value)
        v.setStyleSheet(f"color:{theme.BLUE if accent else theme.TEXT};"
                        "font-size:15px;font-weight:700;background:transparent;")
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
