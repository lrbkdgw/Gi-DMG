"""面板明细弹窗：逐角色列出最终面板与各类加成来源（对应 HTML detailModal）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ...core import state as st
from ...core.constants import EL, TRANS_BONUS_NAMES
from ...core.format import rounded, trim
from .. import icons, theme, widgets as W
from ..session import Session
from ..widgets import hbox, label, vbox
from .base import Modal

DT_NAMES = {"dNA": "普攻", "dCA": "重击", "dPA": "下落", "dE": "战技", "dQ": "爆发"}


def _r2(x: Any) -> str:
    return f"{st.r2(x):g}"


class DetailDialog(Modal):
    def __init__(self, parent, session: Session):
        super().__init__(parent, "面板明细", "chart-no-axes-combined", width=780, height=680)
        res = session.result
        en: List[Dict[str, Any]] = res.get("en", [])
        if not en:
            lb = label("无启用的队伍角色", "Muted")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.add(lb)
            self.finish_body()
            self.add_button("关闭", "", "Primary", self.accept)
            return

        fs, buf, reso = res.get("fs", {}), res.get("buf", {}), res.get("reso", {})
        src_buf = res.get("sourceBuf", {})
        for c in en:
            self.add(self._char_card(c, fs.get(c["id"], {}), buf.get(c["id"], {}),
                                     reso.get(c["id"], {}), src_buf))
        self.finish_body()
        self.add_button("关闭", "", "Primary", self.accept)

    # ------------------------------------------------------------------

    def _char_card(self, c, f, b, r, src_buf) -> QWidget:
        card = W.SubCard(padding=14, spacing=10)

        head = hbox(spacing=8)
        ic = QLabel()
        ic.setPixmap(icons.element_badge(c.get("element", "pyro"), 26))
        head.addWidget(ic)
        nm = label(str(c.get("name", "")))
        nm.setStyleSheet(f"color:{theme.TEXT};font-size:15px;font-weight:700;")
        head.addWidget(nm)
        head.addWidget(label(f"Lv.{int(st.num(c.get('lv'), 90))}", "Muted"))
        head.addStretch(1)
        card.add_layout(head)
        card.add(W.HLine())

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(7)
        stats = [("总攻击力", round(st.numz(f.get("atk")))), ("总防御力", round(st.numz(f.get("def")))),
                 ("总生命值", round(st.numz(f.get("hp")))), ("元素精通", round(st.numz(f.get("em")))),
                 ("暴击率", f"{st.numz(f.get('cr')):.1f}%"), ("暴击伤害", f"{st.numz(f.get('cd')):.1f}%")]
        if st.numz(b.get("defIgnore")):
            stats.append(("无视防御", f"{_r2(b.get('defIgnore'))}%"))
        for i, (k, v) in enumerate(stats):
            cell = QWidget()
            cl = vbox(cell, (0, 0, 0, 0), 1)
            cl.addWidget(label(k, "Muted"))
            val = label(str(v))
            val.setStyleSheet(f"color:{theme.TEXT};font-size:13px;font-weight:700;")
            cl.addWidget(val)
            g.addWidget(cell, i // 4, i % 4)
        card.add_layout(g)

        for title, items in (("面板提升", self._panel_bits(b, r)),
                             ("伤害加成", self._dmg_bits(c, b, r)),
                             ("反应加成", self._reaction_bits(b)),
                             ("月曜加成", self._lunar_bits(b)),
                             ("星烁加成", self._star_bits(b))):
            if items:
                card.add(self._bits_row(title, items))

        src_lines = self._source_bits(c, src_buf)
        if src_lines:
            box = W.SoftCard(padding=9, spacing=4)
            box.add(label("伤害来源定向效果", "FieldLabel"))
            for line in src_lines:
                lb = label("· " + line, "Copy", wrap=True)
                lb.setStyleSheet(f"color:{theme.MUTED};font-size:11.5px;")
                box.add(lb)
            card.add(box)
        return card

    def _bits_row(self, title: str, items: List[str]) -> QWidget:
        box = W.SoftCard(padding=9, spacing=3)
        box.add(label(title, "FieldLabel"))
        lb = label("　|　".join(items), "Copy", wrap=True)
        lb.setStyleSheet(f"color:{theme.TEXT};font-size:11.5px;")
        box.add(lb)
        return box

    # ------------------------------------------------------------------ 各分组

    def _panel_bits(self, b, r) -> List[str]:
        out = []
        for key, name in (("baseAtk", "基础攻击"), ("baseDef", "基础防御"), ("baseHP", "基础生命")):
            if st.numz(b.get(key)):
                out.append(f"{name} +{_r2(b.get(key))}")
        for key, rk, name, unit in (("atkPct", "atkPct", "攻击力", "%"), ("atkFlat", None, "攻击力", ""),
                                    ("defPct", "defPct", "防御力", "%"), ("defFlat", None, "防御力", ""),
                                    ("hpPct", "hpPct", "生命值", "%"), ("hpFlat", None, "生命值", ""),
                                    ("emFlat", "emFlat", "精通", ""),
                                    ("critRate", None, "暴击率", "%"), ("critDMG", None, "暴击伤害", "%")):
            v = st.numz(b.get(key)) + (st.numz(r.get(rk)) if rk else 0)
            if v:
                out.append(f"{name} +{_r2(v)}{unit}")
        return out

    def _dmg_bits(self, c, b, r) -> List[str]:
        out = []
        total_all = st.numz(c.get("allDmgBonus")) + st.numz(r.get("dmgAll")) + st.numz(b.get("dAll"))
        if total_all:
            out.append(f"全伤害 +{total_all:.1f}%")
        for key, name in DT_NAMES.items():
            if st.numz(b.get(key)):
                out.append(f"{name} +{_r2(b.get(key))}%")
        eb = c.get("elemDmgBonus") or {}
        d_elem = b.get("dElem") or {}
        for e in EL:
            v = st.numz(eb.get(e["id"])) + st.numz(d_elem.get(e["id"]))
            if v > 0:
                out.append(f"{e['n']} +{v:.1f}%")
        return out

    def _reaction_bits(self, b) -> List[str]:
        out = []
        if st.numz(b.get("ampBonus")):
            out.append(f"增幅反应 +{_r2(b.get('ampBonus'))}%")
        for k, v in (b.get("transBonus") or {}).items():
            if st.numz(v) > 0:
                out.append(f"{TRANS_BONUS_NAMES.get(k, k)} +{_r2(v)}%")
        return out

    def _lunar_bits(self, b) -> List[str]:
        out = []
        lt = b.get("lunarType") or {}
        lbt = b.get("lunarBaseType") or {}
        if st.numz(b.get("lunarBase")):
            out.append(f"基础区 +{_r2(b.get('lunarBase'))}%")
        for key, name in (("charged", "月感电基础区"), ("bloom", "月绽放基础区"), ("crystal", "月结晶基础区")):
            if st.numz(lbt.get(key)):
                out.append(f"{name} +{_r2(lbt.get(key))}%")
        for key, name in (("lunarAll", "月曜伤害"), ("lunarDirect", "月曜直伤"),
                          ("lunarReaction", "月曜反应")):
            if st.numz(b.get(key)):
                out.append(f"{name} +{_r2(b.get(key))}%")
        asc = st.numz(b.get("specAscend")) or st.numz(b.get("lunarAscend"))
        if asc:
            out.append(f"月曜擢升 +{_r2(asc)}%")
        for key, name in (("charged", "月感电"), ("bloom", "月绽放"), ("crystal", "月结晶")):
            if st.numz(lt.get(key)):
                out.append(f"{name} +{_r2(lt.get(key))}%")
        return out

    def _star_bits(self, b) -> List[str]:
        out = []
        for key, name in (("starBase", "基础区"), ("starBaseSC", "星超导基础区"),
                          ("starBaseSD", "星扩散基础区"), ("starAll", "星烁反应伤害"),
                          ("starBonus", "星超导增伤"), ("starSdBonus", "星扩散增伤")):
            if st.numz(b.get(key)):
                out.append(f"{name} +{_r2(b.get(key))}%")
        if st.numz(b.get("starStacks")):
            out.append(f"星超导叠层 +{_r2(b.get('starStacks'))}层")
        ascends = b.get("starAscends") or []
        if ascends:
            out.append(f"星烁擢升 +{_r2(sum(x * 100 for x in ascends))}%")
        return out

    def _source_bits(self, c, src_buf) -> List[str]:
        lines = []
        for d in c.get("dmgSrcs", []):
            sb = (src_buf or {}).get(d.get("id"))
            if not sb:
                continue
            parts = []
            if st.numz(sb.get("sourceDmgBonus")):
                parts.append(f"伤害提升 +{_r2(sb.get('sourceDmgBonus'))}%")
            if sb.get("finalMults"):
                parts.append("独立乘区 ×" + " ×".join(f"{_r2(m * 100)}%" for m in sb["finalMults"]))
            if st.numz(sb.get("defIgnore")):
                parts.append(f"无视防御 +{_r2(sb.get('defIgnore'))}%")
            if st.numz(sb.get("dAll")):
                parts.append(f"全伤害 +{_r2(sb.get('dAll'))}%")
            for k, name in DT_NAMES.items():
                if st.numz(sb.get(k)):
                    parts.append(f"{name} +{_r2(sb.get(k))}%")
            for e in EL:
                v = (sb.get("dElem") or {}).get(e["id"])
                if st.numz(v):
                    parts.append(f"{e['n']} +{_r2(v)}%")
            if st.numz(sb.get("ampBonus")):
                parts.append(f"增幅反应 +{_r2(sb.get('ampBonus'))}%")
            for k, v in (sb.get("transBonus") or {}).items():
                if st.numz(v):
                    parts.append(f"{TRANS_BONUS_NAMES.get(k, k)} +{_r2(v)}%")
            for key, name, unit in (("starStacks", "星超导叠层", "层"), ("starSdBonus", "星扩散增伤", "%"),
                                    ("specAscend", "月曜擢升", "%"), ("lunarBase", "月曜基础区", "%"),
                                    ("starBase", "星烁基础区", "%"), ("starBaseSC", "星超导基础区", "%"),
                                    ("starBaseSD", "星扩散基础区", "%")):
                if st.numz(sb.get(key)):
                    parts.append(f"{name} +{_r2(sb.get(key))}{unit}")
            lbt = sb.get("lunarBaseType") or {}
            for key, name in (("charged", "月感电基础区"), ("bloom", "月绽放基础区"),
                              ("crystal", "月结晶基础区")):
                if st.numz(lbt.get(key)):
                    parts.append(f"{name} +{_r2(lbt.get(key))}%")
            if sb.get("starAscends"):
                parts.append(f"星烁擢升 +{_r2(sum(x * 100 for x in sb['starAscends']))}%")
            if parts:
                lines.append(f"{d.get('name','')}：" + "、".join(parts))
        return lines


class BaselineSnapshotDialog(Modal):
    """查看某个基准保存时的配置概要。"""

    def __init__(self, parent, session: Session, bid: str):
        b = next((x for x in session.baselines if x.get("id") == bid), None)
        super().__init__(parent, "基准快照", "activity", width=560, height=520)
        if not b:
            self.add(label("找不到该基准。", "Copy"))
            self.finish_body()
            return
        head = W.SoftCard(padding=12, spacing=4)
        head.add(label(f"基准：{b.get('name','')}", "FieldLabel"))
        head.add(label(f"记录时的总伤害：{rounded(b.get('val', 0))}", "Copy"))
        self.add(head)

        cfg = b.get("config") or {}
        chars = cfg.get("chars") or []
        info = W.SubCard(padding=14, spacing=8)
        info.add(label("配置概要", "FieldLabel"))
        info.add(label(f"轴长 {trim(cfg.get('rotationDuration', 20))}s · "
                       f"时间轴{'开启' if cfg.get('timelineEnabled') else '关闭'} · "
                       f"{len(chars)} 名角色", "Copy"))
        for c in chars:
            row = hbox(spacing=7)
            ic = QLabel()
            ic.setPixmap(icons.element_pixmap(c.get("element", "pyro"), 14))
            row.addWidget(ic)
            nm = label(f"{c.get('name','')} Lv.{int(st.num(c.get('lv'), 90))}"
                       f"{'' if c.get('on') else '（未计入）'}")
            nm.setStyleSheet(f"color:{theme.TEXT};font-size:12px;")
            row.addWidget(nm)
            row.addStretch(1)
            row.addWidget(label(f"{len(c.get('dmgSrcs') or [])} 个来源", "Muted"))
            info.add_layout(row)
        self.add(info)
        self.finish_body()
        self.add_button("关闭", "", "Primary", self.accept)


def open_details(parent, session: Session) -> None:
    DetailDialog(parent, session).exec()


def open_baseline_snapshot(parent, session: Session, bid: str) -> None:
    BaselineSnapshotDialog(parent, session, bid).exec()
