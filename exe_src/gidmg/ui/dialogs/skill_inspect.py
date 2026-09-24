"""伤害来源面板时序解析（对应 HTML skillPanelModal）。"""

from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ...core import engine, state as st
from ...core.constants import EL_BY_ID
from ...core.format import rounded, trim
from .. import icons, theme, widgets as W
from ..session import Session
from ..widgets import hbox, label, vbox
from .base import Modal

MODE_NAMES = {"instant": "瞬发出伤", "uniform_snapshot": "持续均匀·锁面板",
              "uniform_dynamic": "持续均匀·随动"}


class SkillInspectDialog(Modal):
    def __init__(self, parent, session: Session, source_id: str):
        super().__init__(parent, "面板时序解析", "activity", width=620, height=640)
        lc = session.result
        item = (lc.get("inspectMap") or {}).get(source_id)
        if not item:
            self.add(label("该伤害来源暂无解析数据，请先完成一次计算。", "Copy", wrap=True))
            self.finish_body()
            self.add_button("关闭", "", "Primary", self.accept)
            return

        d, owner = item["d"], item["owner"]
        start_state = item["startState"]
        en = start_state.get("en", [])
        rot = max(1.0, st.num(session.state.get("rotationDuration"), 20))
        t_start = ((st.numz(d.get("startTime")) % rot) + rot) % rot
        dur = max(0.0, st.numz(d.get("duration")))
        mode = d.get("timingMode") or "instant"
        c = next((x for x in en if x["id"] == (d.get("triggerCharId") or owner["id"])), owner)
        el = d.get("element") if d.get("element") in EL_BY_ID else c.get("element")

        badge = QLabel()
        badge.setPixmap(icons.element_badge(el or "pyro", 22))
        self.add_head(badge)
        self.set_title(f"{owner.get('name','')} · {d.get('name','')} 面板时序解析")

        top = W.SoftCard(padding=11, spacing=5)
        row = hbox(spacing=8)
        m = label(f"出伤模式：{MODE_NAMES.get(mode, mode)}")
        m.setStyleSheet(f"color:{theme.TEXT};font-size:12px;font-weight:700;")
        row.addWidget(m)
        row.addStretch(1)
        e = label(f"总期望：{rounded(item.get('expected', 0))}")
        e.setStyleSheet(f"color:{theme.BLUE};font-size:12px;font-weight:700;")
        row.addWidget(e)
        top.add_layout(row)
        span = (f"技能区间：{trim(t_start)}s"
                + (f" ~ {trim(t_start + dur)}s（持续 {trim(dur)}s，完全均匀出伤）" if dur > 0 else ""))
        top.add(label(span, "Muted", wrap=True))
        self.add(top)

        intervals = engine.get_skill_panel_intervals(session.state, d, owner, en, rot)
        self.add(label(f"持续期间面板变动分段（共 {len(intervals)} 个面板阶段）：", "FieldLabel"))
        for idx, inv in enumerate(intervals):
            self.add(self._interval_card(idx, inv))
        self.finish_body()
        self.add_button("关闭", "", "Primary", self.accept)

    def _interval_card(self, idx: int, inv: Dict[str, Any]) -> QWidget:
        card = W.SubCard(padding=11, spacing=8)
        head = hbox(spacing=7)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{theme.BLUE};border-radius:4px;")
        head.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        title = (f"阶段 {idx + 1}：瞬发出伤时刻（{trim(inv['start'])}s）" if inv["duration"] == 0
                 else f"阶段 {idx + 1}：{trim(inv['start'])}s ~ {trim(inv['end'])}s"
                      f"（持续 {trim(inv['duration'])}s）")
        t = label(title)
        t.setStyleSheet(f"color:{theme.TEXT};font-size:11.5px;font-weight:700;")
        head.addWidget(t, 1)
        if inv.get("isSnapshot"):
            head.addWidget(W.Pill("锁面板", theme.WARN, theme.WARN_TINT))
        else:
            head.addWidget(W.Pill("随动结算", theme.BLUE, theme.BLUE_TINT))
        card.add_layout(head)

        f = inv["fs"]
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(5)
        stats = [("攻击力", round(st.numz(f.get("atk")))), ("防御力", round(st.numz(f.get("def")))),
                 ("生命值", round(st.numz(f.get("hp")))), ("元素精通", round(st.numz(f.get("em")))),
                 ("暴击率", f"{st.numz(f.get('cr')):.1f}%"), ("暴击伤害", f"{st.numz(f.get('cd')):.1f}%")]
        for i, (k, v) in enumerate(stats):
            cell = QWidget()
            cl = hbox(cell, (0, 0, 0, 0), 4)
            cl.addWidget(label(k + "：", "Muted"))
            val = label(str(v))
            val.setStyleSheet(f"color:{theme.TEXT};font-size:11.5px;font-weight:700;")
            cl.addWidget(val)
            cl.addStretch(1)
            g.addWidget(cell, i // 3, i % 3)
        card.add_layout(g)

        tal_row = hbox(spacing=5)
        tal_row.addWidget(label("生效天赋：", "Muted"))
        talents = inv.get("talents") or []
        if talents:
            host = QWidget()
            flow = W.FlowLayout(host, h_spacing=5, v_spacing=4)
            for t in talents:
                flow.addWidget(W.Pill(str(t.get("name", "")), theme.MUTED, theme.SURFACE_SUBTLE))
            tal_row.addWidget(host, 1)
        else:
            lb = label("无额外生效天赋", "Muted")
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11px;")
            tal_row.addWidget(lb, 1)
        card.add_layout(tal_row)
        return card


def open_skill_inspect(parent, session: Session, source_id: str) -> None:
    SkillInspectDialog(parent, session, source_id).exec()
