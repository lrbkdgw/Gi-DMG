"""右侧栏：基准值 + 伤害统计 + 总期望/DPS。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QInputDialog, QLabel, QSizePolicy, QWidget

from ..core import state as st
from ..core.constants import EL_BY_ID
from ..core.format import rounded, dps as fmt_dps
from . import icons, motion, theme, widgets as W
from .session import Session
from .widgets import button, clear_layout, hbox, icon_button, label, vbox


TIMING_TAGS = {
    "instant": ("瞬发", "#5b6470", "#eef1f5"),
    "uniform_snapshot": ("锁面板", "#b06000", "#fef7e0"),
    "uniform_dynamic": ("随动", "#1967d2", "#e8f0fe"),
}


class ResultRow(QFrame):
    """单条伤害来源的结算结果卡。"""

    inspect = Signal(str)

    def __init__(self, r: Dict[str, Any], timeline_on: bool, parent=None):
        super().__init__(parent)
        self.source_id = r.get("sourceId", "")
        self.setObjectName("ResRow")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._hover = motion.HoverTracker(self, motion.CONTROL)
        lay = vbox(self, (10, 9, 10, 9), 4)

        head = hbox(spacing=5)
        owner, panel = r.get("ownerName", ""), r.get("charName", "")
        name_txt = owner if owner == panel else f"{owner}"
        title = label(f"{name_txt} · {r.get('dName','')}")
        title.setStyleSheet(f"color:{theme.TEXT};font-size:12px;font-weight:700;")
        head.addWidget(title)
        if owner != panel:
            head.addWidget(W.Pill(f"{panel}面板", theme.MUTED, "transparent", bold=False))
        head.addStretch(1)

        elem = r.get("elem", "")
        if elem:
            badge = QLabel()
            badge.setPixmap(icons.element_pixmap(elem, 15))
            badge.setToolTip(EL_BY_ID.get(elem, {}).get("n", elem))
            badge.setStyleSheet("background:transparent;")
            head.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(head)

        tags = hbox(spacing=4)
        if r.get("isSpecDirect"):
            tags.addWidget(W.Pill("特殊直伤", "#8f5fa3"))
        if r.get("isSpecReaction"):
            tags.addWidget(W.Pill("特殊反应", "#8f5fa3"))
        if timeline_on:
            mode = r.get("timingMode", "instant")
            text, color, bg = TIMING_TAGS.get(mode, TIMING_TAGS["instant"])
            start = st.r2(r.get("startTime", 0))
            if mode == "instant":
                tag = f"{text} {start:g}s"
            else:
                tag = f"{text} {start:g}~{st.r2(start + st.numz(r.get('duration'))):g}s"
            tags.addWidget(W.Pill(tag, color, bg, bold=False))
        tags.addStretch(1)
        if tags.count() > 1:
            lay.addLayout(tags)

        val = hbox(spacing=5)
        val.addWidget(label("总期望", "Muted"))
        big = label(rounded(r.get("expected", 0)))
        big.setStyleSheet(f"color:{theme.TEXT_STRONG};font-size:14px;font-weight:700;")
        val.addWidget(big)
        val.addStretch(1)
        lay.addLayout(val)

        crit, non = rounded(r.get("crit", 0)), rounded(r.get("nonCrit", 0))
        if r.get("isQuicken"):
            detail = f"暴击 {crit} / 未暴击 {non}（激化）"
        elif r.get("isTrans"):
            detail = f"总计 {non}（不可暴击）"
        elif r.get("isSpecReaction"):
            detail = f"总期望 {rounded(r.get('expected', 0))} / 可暴击"
        elif r.get("isSpecDirect"):
            detail = f"暴击 {crit} / 非暴击 {non}"
        else:
            detail = f"暴击 {crit} / 未暴击 {non}"
        d = label(detail, "Muted")
        d.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:10.5px;")
        lay.addWidget(d)

    def paintEvent(self, _ev) -> None:
        # #resList .sc：浅灰卡片、14px 圆角；悬停时渐变到蓝色浅底
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._hover.hover
        bg = motion.mix_color(theme.SURFACE_SUBTLE, theme.BLUE_TINT, t)
        border = motion.mix_color(QColor(0, 0, 0, 0), theme.BLUE_BORDER, t)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen if border.alpha() == 0 else QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, theme.RADIUS_MD, theme.RADIUS_MD)
        p.end()

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.inspect.emit(self.source_id)
        ev.accept()


class ResultsPanel(QWidget):
    """右侧统计栏。"""

    inspectSource = Signal(str)
    showDetails = Signal()
    showDmgShare = Signal()
    viewBaseline = Signal(str)
    restoreBaseline = Signal(str)

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        self.setObjectName("Surface")
        self.setStyleSheet(f"QWidget#Surface {{ background:{theme.SURFACE}; "
                           f"border-left:1px solid {theme.BORDER}; }}")

        root = vbox(self, (0, 0, 0, 0), 0)
        scroll = W.ScrollArea(margins=(12, 14, 12, 16), spacing=12)
        root.addWidget(scroll, 1)

        card = W.Card(kind="ResultsCard", padding=15, spacing=10, with_shadow=False)
        scroll.add(card)
        scroll.body.addStretch(1)

        # ---------------- 基准值
        b_head = hbox(spacing=8)
        self.base_title = label("基准值", "SubHeading")
        self.base_title.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;")
        b_head.addWidget(self.base_title)
        b_head.addStretch(1)
        self.add_base_btn = button("+ 设为新基准", "", "Link", card, self._add_baseline)
        b_head.addWidget(self.add_base_btn)
        card.add_layout(b_head)

        self.base_host = QWidget()
        self.base_lay = vbox(self.base_host, (0, 0, 0, 0), 5)
        card.add(self.base_host)

        self.mode_row = QWidget()
        mr = hbox(self.mode_row, (8, 6, 8, 6), 8)
        self.mode_row.setStyleSheet(f"background:{theme.SURFACE_SUBTLE};border-radius:10px;")
        mr.addWidget(label("基准对比模式", "Muted"), 1)
        self.mode_btn = button("当前 vs 基准", "", "", self.mode_row, self._flip_mode)
        self.mode_btn.setStyleSheet("font-size:11px;padding:0 10px;min-height:26px;")
        self.mode_btn.set_skin(bg=theme.SURFACE)
        mr.addWidget(self.mode_btn)
        card.add(self.mode_row)

        card.add(W.HLine())

        # ---------------- 伤害统计
        s_head = hbox(spacing=6)
        t = label("伤害统计")
        t.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;")
        s_head.addWidget(t)
        s_head.addStretch(1)
        s_head.addWidget(icon_button("chart-no-axes-combined", "面板明细", card,
                                     self.showDetails.emit, size=15))
        self.share_btn = icon_button("pie-chart", "角色伤害占比", card, self.showDmgShare.emit, size=15)
        s_head.addWidget(self.share_btn)
        card.add_layout(s_head)

        self.res_host = QWidget()
        self.res_lay = vbox(self.res_host, (0, 0, 0, 0), 7)
        card.add(self.res_host)

        card.add(W.HLine())

        total_row = hbox(spacing=8)
        total_row.addWidget(label("总期望伤害", "Copy"), 1)
        self.total_lb = label("0", "Metric")
        total_row.addWidget(self.total_lb, 0, Qt.AlignmentFlag.AlignBottom)
        card.add_layout(total_row)

        self.dps_row = QWidget()
        dr = hbox(self.dps_row, (0, 0, 0, 0), 8)
        dr.addWidget(label("全队秒伤 (DPS)", "Muted"), 1)
        self.dps_lb = label("0/s", "MetricSmall")
        dr.addWidget(self.dps_lb, 0, Qt.AlignmentFlag.AlignBottom)
        card.add(self.dps_row)

        session.calcFinished.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        res = self.s.result
        rows: List[Dict[str, Any]] = res.get("results", [])

        clear_layout(self.res_lay)
        if not rows:
            empty = label("暂无启用的伤害来源。", "Muted")
            empty.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:12px;padding:6px 2px;")
            self.res_lay.addWidget(empty)
        else:
            for r in rows:
                row = ResultRow(r, self.s.timeline_on, self.res_host)
                row.inspect.connect(self.inspectSource.emit)
                self.res_lay.addWidget(row)

        self.total_lb.setText(rounded(res.get("total", 0)))
        self.dps_row.setVisible(self.s.timeline_on)
        self.dps_lb.setText(fmt_dps(res.get("dps", 0)))
        self.share_btn.setVisible(self.s.share_on)
        self._refresh_baselines()

    def _refresh_baselines(self) -> None:
        clear_layout(self.base_lay)
        bases = self.s.baselines
        mode = self.s.state.get("baselineMode", "a")
        self.mode_btn.setText("当前 vs 基准" if mode == "a" else "基准 vs 当前")
        self.mode_row.setVisible(bool(bases))
        if not bases:
            lb = label("暂无基准值，可将当前伤害保存以作对比。", "Muted", wrap=True)
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11.5px;")
            self.base_lay.addWidget(lb)
            return

        total = float(self.s.result.get("total", 0.0))
        for b in bases:
            val = float(b.get("val", 0.0))
            if mode == "a":
                diff = (total - val) / val * 100 if val > 0 else 0.0
            else:
                diff = (val - total) / total * 100 if total > 0 else 0.0
            row = QFrame(self.base_host)
            row.setStyleSheet(f"background:{theme.SURFACE_SUBTLE};border-radius:10px;")
            rl = hbox(row, (8, 5, 6, 5), 6)

            name_btn = button(str(b.get("name", "基准")), "", "Link", row,
                              lambda bid=b["id"]: self.viewBaseline.emit(bid))
            name_btn.setStyleSheet("font-size:11.5px;font-weight:600;")
            name_btn.set_skin(fg=theme.TEXT, hover_fg=theme.BLUE)
            rl.addWidget(name_btn)
            rl.addWidget(label(f"({rounded(val)})", "Muted"))
            rl.addStretch(1)

            color = theme.OK if diff > 0 else (theme.DANGER if diff < 0 else theme.MUTED)
            pct = label(f"{'+' if diff >= 0 else ''}{diff:.1f}%")
            pct.setStyleSheet(f"color:{color};font-size:11.5px;font-weight:700;")
            rl.addWidget(pct)

            rl.addWidget(icon_button("rotate-ccw", "把该基准的配置设为当前", row,
                                     lambda bid=b["id"]: self.restoreBaseline.emit(bid),
                                     size=13))
            rl.addWidget(icon_button("x", "删除基准", row,
                                     lambda bid=b["id"]: self._remove(bid), size=13))
            self.base_lay.addWidget(row)

    # ------------------------------------------------------------------

    def _add_baseline(self) -> None:
        name, ok = QInputDialog.getText(self, "设为新基准", "基准名称：",
                                        text=f"基准 {len(self.s.baselines) + 1}")
        if ok:
            self.s.add_baseline(name.strip() or f"基准 {len(self.s.baselines) + 1}")
            self._refresh_baselines()

    def _remove(self, bid: str) -> None:
        self.s.remove_baseline(bid)
        self._refresh_baselines()

    def _flip_mode(self) -> None:
        self.s.state["baselineMode"] = "b" if self.s.state.get("baselineMode", "a") == "a" else "a"
        self.s.touch()
        self._refresh_baselines()
