"""中央工作区：角色配置（面板属性 / 伤害来源 / 天赋增益）。

与 HTML 的 rEditor() + rDmg() + rTal() 一一对应。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QLabel, QMenu, QSizePolicy, QSlider,
                               QWidget)

from ..core import state as st
from ..core.constants import DT, EL, SPECIAL_REACTIONS, TRANS_REACTIONS
from ..core.engine import (active_talents, equipment_talents, get_star_stacks,
                           star_coeff_from_stacks)
from . import icons, theme, widgets as W
from .effects import EffectList, char_options, describe_effect
from .session import Session
from .widgets import button, chip, clear_layout, hbox, icon_button, label, vbox

STAT_OPTS = [("", "选择属性"), ("atk", "攻击力"), ("def", "防御力"), ("hp", "生命值"),
             ("em", "元素精通"), ("fixed", "固定值")]
REACTION_OPTS = [("", "选择反应"), ("none", "无"), ("vape", "蒸发"), ("melt", "融化")]
TIMING_OPTS = [("instant", "瞬发出伤"), ("uniform_snapshot", "持续均匀·锁面板"),
               ("uniform_dynamic", "持续均匀·随动")]
EL_OPTS = [("", "选择元素")] + [(e["id"], e["n"]) for e in EL]
DT_OPTS = [("", "选择类型")] + [(t["id"], t["n"]) for t in DT]
TRANS_OPTS = [("", "选择反应")] + [(r["id"], r["n"]) for r in TRANS_REACTIONS]
SPEC_DIRECT_OPTS = [("", "选择类型")] + [(r["id"], r["n"]) for r in SPECIAL_REACTIONS if r.get("direct")]
SPEC_REACT_OPTS = [("", "选择类型")] + [(r["id"], r["n"]) for r in SPECIAL_REACTIONS if not r.get("direct")]
SPEC_META = {r["id"]: r for r in SPECIAL_REACTIONS}


def _small(w: QWidget) -> QWidget:
    w.setStyleSheet("min-height:26px;font-size:11px;padding:0 7px;")
    return w


def _mini_field(text: str, w: QWidget) -> QWidget:
    box = QWidget()
    lay = vbox(box, (0, 0, 0, 0), 3)
    lb = label(text)
    lb.setStyleSheet(f"color:{theme.MUTED};font-size:10.5px;")
    lay.addWidget(lb)
    lay.addWidget(_small(w))
    return box


class EditorSection(W.Card):
    """编辑器里的一个分区（标题 + 右侧操作 + 内容）。"""

    def __init__(self, title: str, parent=None, action: Optional[QWidget] = None,
                 kind: str = "SubCard", padding: int = 14):
        super().__init__(parent, kind, padding, 10, with_shadow=False)
        head = hbox(spacing=8)
        t = label(title)
        t.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        head.addWidget(t)
        head.addStretch(1)
        if action is not None:
            head.addWidget(action)
        self.head = head
        self.body.addLayout(head)


# ====================================================================== 伤害来源

class DmgSourceCard(QFrame):
    """一条伤害来源。"""

    changed = Signal()
    structureChanged = Signal()
    removed = Signal(str)

    def __init__(self, session: Session, char: Dict[str, Any], d: Dict[str, Any],
                 parent=None, locked: bool = False):
        super().__init__(parent)
        self.s = session
        self.char = char
        self.d = d
        self.locked = locked
        self.setObjectName("DmgCard")
        self._apply_border()

        lay = vbox(self, (12, 10, 12, 12), 9)

        # ---------------- 标题行
        head = hbox(spacing=7)
        self.name = W.TextField(str(d.get("name", "")))
        self.name.textEdited.connect(self._on_name)
        head.addWidget(self.name, 1)
        self.toggle = W.ToggleSwitch(bool(d.get("on")), scale=0.85)
        self.toggle.toggled.connect(self._on_toggle)
        head.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        if not locked:
            head.addWidget(icon_button("trash-2", "删除该伤害来源", self,
                                       lambda: self.removed.emit(d["id"]), size=14))
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        lay.addLayout(grid)
        self.grid = grid
        self._row = 0

        kind = d.get("type", "normal")
        if kind == "trans":
            self._build_trans()
        elif kind == "special_direct":
            self._build_special_direct()
        elif kind == "special_reaction":
            self._build_special_reaction()
        else:
            self._build_normal()

        if self.s.timeline_on:
            lay.addWidget(W.HLine())
            lay.addLayout(self._build_timing())

        if locked:
            for w in self.findChildren(QWidget):
                if w is not self.name and isinstance(w, (W.Select, W.NumField, W.ToggleSwitch)):
                    w.setEnabled(False)

    # ------------------------------------------------------------------ 构件

    def _cell(self, text: str, w: QWidget, span: int = 1) -> None:
        self.grid.addWidget(_mini_field(text, w), self._row // 3, self._row % 3, 1, span)
        self._row += span

    def _select(self, key: str, options, rebuild: bool = True) -> W.Select:
        sel = W.Select(options, str(self.d.get(key, "") or ""))
        sel.picked.connect(lambda v, k=key: self._set(k, v, rebuild))
        return sel

    def _numeric(self, key: str, default: float = 0.0, decimals: int = 3) -> W.NumField:
        f = W.NumField(self.d.get(key, default), default, decimals=decimals)
        f.edited.connect(lambda v, k=key: self._set(k, v, False))
        return f

    def _chars(self):
        return char_options(self.s.state)

    # ------------------------------------------------------------------ 各类型

    def _build_normal(self) -> None:
        self._cell("伤害归属", self._select("triggerCharId", self._chars()))
        self._cell("计入属性归属", self._select("statCharId", self._chars()))
        self._cell("计入属性", self._select("stat", STAT_OPTS))
        self._cell("总倍率 %", self._numeric("mult", 100))
        if self.d.get("stat") == "fixed":
            self._cell("固定值", self._numeric("fixedBase"))
        self._cell("元素", self._select("element", EL_OPTS))
        self._cell("伤害类型", self._select("dmgType", DT_OPTS))
        self._cell("反应", self._select("reaction", REACTION_OPTS))

    def _build_trans(self) -> None:
        self._cell("触发角色面板", self._select("triggerCharId", self._chars()))
        self._cell("反应类型", self._select("transType", TRANS_OPTS))
        self._cell("段数", self._numeric("triggerCount", 1, decimals=0))

    def _build_special_direct(self) -> None:
        self._cell("伤害归属", self._select("triggerCharId", self._chars()))
        self._cell("计入属性归属", self._select("statCharId", self._chars()))
        self._cell("特殊直伤类型", self._select("specType", SPEC_DIRECT_OPTS))
        self._cell("计入属性", self._select("stat", STAT_OPTS))
        self._cell("总倍率 %", self._numeric("mult", 100))
        if self.d.get("stat") == "fixed":
            self._cell("固定值", self._numeric("fixedBase"))
        if self.d.get("specType") == "star_sc_direct":
            self._add_star_slider()

    def _add_star_slider(self) -> None:
        stacks = int(get_star_stacks(self.d))
        box = W.SoftCard(padding=9, spacing=6)
        head = hbox(spacing=6)
        head.addWidget(label("星超导领域层数", "Muted"), 1)
        badge = label(f"{stacks} 层 · {star_coeff_from_stacks(stacks):.2f}")
        badge.setStyleSheet(f"color:{theme.BLUE};font-size:11px;font-weight:700;")
        head.addWidget(badge)
        box.add_layout(head)

        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(0, 12)
        sl.setValue(stacks)
        sl.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height:4px; background:{theme.BORDER}; border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:{theme.BLUE}; border-radius:2px; }}
            QSlider::handle:horizontal {{ width:14px; height:14px; margin:-5px 0;
                background:{theme.BLUE}; border:2px solid #fff; border-radius:7px; }}
        """)

        def on_move(v: int) -> None:
            badge.setText(f"{v} 层 · {star_coeff_from_stacks(v):.2f}")
            self._set("starStacks", float(v), rebuild=False)

        sl.valueChanged.connect(on_move)
        box.add(sl)
        row = self._row // 3 + (1 if self._row % 3 else 0)
        self.grid.addWidget(box, row, 0, 1, 3)
        self._row = (row + 1) * 3

    def _build_special_reaction(self) -> None:
        holder = QWidget()
        hl = vbox(holder, (0, 0, 0, 0), 5)
        hl.addWidget(label("伤害归属（点击选择，可多选）", "Muted"))
        chips_host = QWidget()
        flow = W.FlowLayout(chips_host, h_spacing=5, v_spacing=5)
        picks = list(self.d.setdefault("contribs", []))
        enabled = self.s.enabled_chars
        if not enabled:
            flow.addWidget(label("无可用角色", "Muted"))
        for c in enabled:
            b = chip(str(c.get("name", "")), chips_host, checkable=True)
            b.setChecked(c["id"] in picks)
            b.clicked.connect(lambda checked, cid=c["id"]: self._toggle_contrib(cid, checked))
            b.setEnabled(not self.locked)
            flow.addWidget(b)
        hl.addWidget(chips_host)
        self.grid.addWidget(holder, 0, 0, 1, 3)
        self._row = 3

        self._cell("特殊反应类型", self._select("specType", SPEC_REACT_OPTS))
        meta = SPEC_META.get(self.d.get("specType", ""))
        if meta and meta.get("cryoChoice"):
            cur = self.d.get("starSwirlCryoMult")
            sel = W.Select([("", "选择系数"), ("2", "2"), ("3", "3")],
                           str(int(cur)) if cur else "")
            sel.picked.connect(lambda v: self._set("starSwirlCryoMult",
                                                   st.numz(v) if v else "", True))
            self._cell("系数", sel)
        self._cell("段数", self._numeric("triggerCount", 1, decimals=0))

    def _build_timing(self):
        lay = vbox(spacing=7)
        row = hbox(spacing=8)
        mode = self.d.get("timingMode") or "instant"
        sel = W.Select(TIMING_OPTS, mode)
        sel.picked.connect(lambda v: self._set("timingMode", v, True))
        row.addWidget(_mini_field("出伤模式", sel), 1)
        row.addWidget(_mini_field("开始时间(s)", self._numeric("startTime")), 1)
        if mode != "instant":
            row.addWidget(_mini_field("持续时间(s)", self._numeric("duration")), 1)
        else:
            row.addStretch(1)
        lay.addLayout(row)
        if mode != "instant":
            hint = label("※ 倍率为持续时间内的总倍率，将完全均匀分摊出伤。", "Muted", wrap=True)
            hint.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:10px;")
            lay.addWidget(hint)
        return lay

    # ------------------------------------------------------------------ 行为

    def _apply_border(self) -> None:
        bad = st.dmg_source_incomplete(self.d)
        color = theme.DANGER if bad else theme.BORDER
        self.setStyleSheet(f"QFrame#DmgCard {{ background:{theme.SURFACE}; "
                           f"border:1px solid {color}; border-radius:14px; }}")

    def _set(self, key: str, value: Any, rebuild: bool = True) -> None:
        self.d[key] = value
        self._apply_border()
        if rebuild:
            self.structureChanged.emit()
        else:
            self.changed.emit()

    def _on_name(self, text: str) -> None:
        self.d["name"] = text
        self.changed.emit()

    def _on_toggle(self, value: bool) -> None:
        self.d["on"] = value
        self.changed.emit()

    def _toggle_contrib(self, cid: str, checked: bool) -> None:
        picks = self.d.setdefault("contribs", [])
        if checked and cid not in picks:
            picks.append(cid)
        elif not checked and cid in picks:
            picks.remove(cid)
        self._apply_border()
        self.changed.emit()


# ====================================================================== 天赋

class TalentCard(QFrame):
    changed = Signal()
    structureChanged = Signal()
    removed = Signal(str)

    def __init__(self, session: Session, t: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.s = session
        self.t = t
        self.setObjectName("TalCard")
        self._apply_border()
        lay = vbox(self, (12, 10, 12, 12), 9)

        head = hbox(spacing=7)
        self.name = W.TextField(str(t.get("name", "")))
        self.name.textEdited.connect(self._on_name)
        head.addWidget(self.name, 1)
        self.toggle = W.ToggleSwitch(bool(t.get("on")), scale=0.85)
        self.toggle.toggled.connect(self._on_toggle)
        head.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(icon_button("trash-2", "删除该天赋", self,
                                   lambda: self.removed.emit(t["id"]), size=14))
        lay.addLayout(head)

        if session.timeline_on:
            box = QWidget()
            box.setStyleSheet(f"background:{theme.SURFACE_SUBTLE};border-radius:8px;")
            bl = hbox(box, (9, 5, 9, 5), 8)
            bl.addWidget(label("生效区间", "Muted"))
            bl.addStretch(1)
            bl.addWidget(label("开始", "Muted"))
            f1 = W.NumField(t.get("startTime", 0), 0, decimals=2, width=62)
            f1.edited.connect(lambda v: self._set("startTime", v))
            bl.addWidget(_small(f1))
            bl.addWidget(label("持续", "Muted"))
            f2 = W.NumField(t.get("duration", 20), 20, decimals=2, width=62)
            f2.edited.connect(lambda v: self._set("duration", v))
            bl.addWidget(_small(f2))
            lay.addWidget(box)

        self.effects = EffectList(session.state, t.setdefault("effs", []), self)
        self.effects.changed.connect(self._on_eff_changed)
        lay.addWidget(self.effects)

    def _apply_border(self) -> None:
        ok = st.talent_valid(self.t)
        color = theme.BORDER if ok else theme.DANGER
        self.setStyleSheet(f"QFrame#TalCard {{ background:{theme.SURFACE}; "
                           f"border:1px solid {color}; border-radius:14px; }}")

    def _set(self, key: str, value: Any) -> None:
        self.t[key] = value
        self.changed.emit()

    def _on_name(self, text: str) -> None:
        self.t["name"] = text
        self.changed.emit()

    def _on_toggle(self, value: bool) -> None:
        self.t["on"] = value
        self.changed.emit()

    def _on_eff_changed(self) -> None:
        self._apply_border()
        self.changed.emit()


# ====================================================================== 主面板

class CharacterPanel(QWidget):
    """角色配置工作区。"""

    openQuickSetter = Signal()
    quickTableSaveScheme = Signal()

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.s = session
        self.quick_table_mode = False
        self._pending_focus: Optional[str] = None

        lay = vbox(self, (0, 0, 0, 0), 0)
        self.empty = W.EmptyState("user-round-plus", "从左侧添加并选择角色",
                                  "角色面板、伤害来源与天赋配置会显示在这里。")
        self.card = W.Card(padding=20, spacing=14)
        lay.addWidget(self.empty)
        lay.addWidget(self.card)
        lay.addStretch(1)

        self.content = QWidget()
        self.content_lay = vbox(self.content, (0, 0, 0, 0), 14)
        self.card.add(self.content)

        session.selectionChanged.connect(self.rebuild)
        session.editorChanged.connect(self.rebuild)
        session.calcFinished.connect(self._refresh_readouts)
        self.rebuild()

    # ------------------------------------------------------------------

    def set_quick_table_mode(self, on: bool) -> None:
        self.quick_table_mode = on
        self.rebuild()

    def rebuild(self) -> None:
        ch = self.s.selected
        self.empty.setVisible(ch is None)
        self.card.setVisible(ch is not None)
        clear_layout(self.content_lay)
        if ch is None:
            return
        self.char = ch
        self.content_lay.addLayout(self._identity_row(ch))
        self.content_lay.addWidget(self._panel_section(ch))
        self.content_lay.addWidget(self._sources_section(ch))
        self.content_lay.addWidget(self._talents_section(ch))
        self._refresh_readouts()

    # ------------------------------------------------------------------ 头部

    def _identity_row(self, ch: Dict[str, Any]):
        row = hbox(spacing=8)
        name = W.TextField(str(ch.get("name", "")))
        name.textEdited.connect(lambda t: self._set_char("name", t, chars=True))
        row.addWidget(W.field("角色名", name), 3)

        lv = W.NumField(ch.get("lv", 90), 90, decimals=0, allow_negative=False)
        lv.edited.connect(lambda v: self._set_char("lv", v, chars=True))
        row.addWidget(W.field("等级", lv), 1)

        el = W.Select([(e["id"], e["n"]) for e in EL], ch.get("element", "pyro"))
        el.picked.connect(lambda v: self._set_char("element", v, chars=True, rebuild=True))
        row.addWidget(W.field("元素", el), 2)

        if not self.quick_table_mode:
            btns = vbox(spacing=4)
            btns.addSpacing(17)
            b = hbox(spacing=4)
            b.addWidget(icon_button("copy", "复制该角色", self,
                                    lambda: self.s.duplicate_char(ch["id"])))
            b.addWidget(icon_button("trash-2", "删除该角色", self,
                                    lambda: self.s.remove_char(ch["id"])))
            btns.addLayout(b)
            row.addLayout(btns, 0)
        return row

    # ------------------------------------------------------------------ 面板属性

    def _panel_section(self, ch: Dict[str, Any]) -> QWidget:
        qs_btn = button("+ 快捷配置助手", "", "Link", None, self.openQuickSetter.emit)
        sec = EditorSection("面板属性", self, qs_btn)

        def grid(fields, cols: int):
            g = QGridLayout()
            g.setContentsMargins(0, 0, 0, 0)
            g.setHorizontalSpacing(8)
            g.setVerticalSpacing(8)
            for i, (title, key, default) in enumerate(fields):
                f = W.NumField(ch.get(key, default), default, decimals=3)
                f.edited.connect(lambda v, k=key: self._set_char(k, v))
                g.addWidget(W.field(title, f), i // cols, i % cols)
            return g

        sec.add_layout(grid([("基础攻击力", "baseAtk", 0), ("武器攻击力", "weaponAtk", 0),
                             ("攻击力 %", "atkPct", 0), ("固定攻击力", "atkFlat", 0)], 4))
        sec.add_layout(grid([("基础生命值", "baseHP", 0), ("生命值 %", "hpPct", 0),
                             ("固定生命值", "hpFlat", 0)], 3))
        sec.add_layout(grid([("基础防御力", "baseDef", 0), ("防御力 %", "defPct", 0),
                             ("固定防御力", "defFlat", 0)], 3))
        sec.add_layout(grid([("元素精通", "em", 0), ("暴击率 %", "critRate", 5),
                             ("暴击伤害 %", "critDMG", 50), ("全伤害加成 %", "allDmgBonus", 0)], 4))

        sec.add(label("各元素/物理伤害加成 %", "FieldLabel"))
        eb_grid = QGridLayout()
        eb_grid.setContentsMargins(0, 0, 0, 0)
        eb_grid.setHorizontalSpacing(7)
        eb_grid.setVerticalSpacing(7)
        eb = ch.setdefault("elemDmgBonus", st.def_eb())
        for i, e in enumerate(EL):
            cell = QWidget()
            cl = vbox(cell, (0, 0, 0, 0), 3)
            head = hbox(spacing=4)
            head.addStretch(1)
            ic = QLabel()
            ic.setPixmap(icons.element_pixmap(e["id"], 14))
            head.addWidget(ic)
            nm = label(e["n"])
            nm.setStyleSheet(f"color:{theme.element_color(e['id'])};font-size:10.5px;font-weight:700;")
            head.addWidget(nm)
            head.addStretch(1)
            cl.addLayout(head)
            f = W.NumField(eb.get(e["id"], 0), 0, decimals=3)
            f.setAlignment(Qt.AlignmentFlag.AlignCenter)
            f.edited.connect(lambda v, k=e["id"]: self._set_eb(k, v))
            cl.addWidget(f)
            eb_grid.addWidget(cell, i // 4, i % 4)
        sec.add_layout(eb_grid)

        self.readout = QWidget()
        rl = hbox(self.readout, (10, 8, 10, 8), 6)
        self.readout.setStyleSheet(f"background:{theme.BLUE_TINT};border-radius:10px;")
        self.readout_label = label("", "Copy", wrap=True)
        self.readout_label.setStyleSheet(f"color:{theme.BLUE};font-size:11.5px;")
        rl.addWidget(self.readout_label, 1)
        sec.add(self.readout)

        self.equipped_host = QWidget()
        self.equipped_lay = vbox(self.equipped_host, (0, 0, 0, 0), 6)
        sec.add(self.equipped_host)
        return sec

    # ------------------------------------------------------------------ 伤害来源

    def _sources_section(self, ch: Dict[str, Any]) -> QWidget:
        add = icon_button("plus", "添加伤害来源", None, None, theme.BLUE, 15, "AddBtn")
        menu = QMenu(add)
        for text, kind in (("普通伤害", "normal"), ("剧变反应", "trans"),
                           ("特殊直伤", "special_direct"), ("特殊反应", "special_reaction")):
            menu.addAction(f"+ {text}", lambda k=kind: self._add_source(k))
        add.setMenu(menu)
        add.setVisible(not self.quick_table_mode)

        sec = EditorSection("伤害来源", self, add)
        host = QWidget()
        lay = vbox(host, (0, 0, 0, 0), 9)
        sources = ch.setdefault("dmgSrcs", [])
        if not sources:
            lay.addWidget(self._hint("暂无伤害来源。点击右上角 + 添加。"))
        for d in sources:
            card = DmgSourceCard(self.s, ch, d, host, self.quick_table_mode)
            card.changed.connect(self._touch)
            card.structureChanged.connect(self._rebuild_soon)
            card.removed.connect(self._remove_source)
            lay.addWidget(card)
        sec.add(host)
        return sec

    # ------------------------------------------------------------------ 天赋

    def _talents_section(self, ch: Dict[str, Any]) -> QWidget:
        add = icon_button("plus", "添加天赋", None, self._add_talent, theme.BLUE, 15, "AddBtn")
        sec = EditorSection("天赋 / 增益", self, add)
        host = QWidget()
        lay = vbox(host, (0, 0, 0, 0), 9)
        manual = [t for t in ch.setdefault("talents", [])
                  if not t.get("source") or t.get("source") == "manual"]
        if not manual:
            lay.addWidget(self._hint("暂无天赋。"))
        for t in manual:
            t["source"] = "manual"
            t["isPermanent"] = False
            card = TalentCard(self.s, t, host)
            card.changed.connect(self._touch)
            card.structureChanged.connect(self._rebuild_soon)
            card.removed.connect(self._remove_talent)
            lay.addWidget(card)
        sec.add(host)
        return sec

    def _hint(self, text: str) -> QLabel:
        lb = label(text, "Muted")
        lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11.5px;padding:4px 2px;")
        return lb

    # ------------------------------------------------------------------ 读数

    def _refresh_readouts(self) -> None:
        ch = self.s.selected
        if ch is None or not hasattr(self, "readout_label"):
            return
        self.readout_label.setText(
            f"基础面板：总攻击力 <b>{round(st.final_atk(ch))}</b> · "
            f"总防御力 <b>{round(st.final_def(ch))}</b> · "
            f"总生命值 <b>{round(st.final_hp(ch))}</b>")
        self.readout_label.setTextFormat(Qt.TextFormat.RichText)
        self._refresh_equipped(ch)

    def _refresh_equipped(self, ch: Dict[str, Any]) -> None:
        clear_layout(self.equipped_lay)
        talents = equipment_talents(ch)
        if not talents:
            return
        box = W.SoftCard(padding=10, spacing=6)
        box.add(label("已装备效果（来自快捷配置助手）", "FieldLabel"))
        for t in talents:
            row = hbox(spacing=6)
            dot = QLabel()
            dot.setFixedSize(6, 6)
            on = bool(t.get("on"))
            dot.setStyleSheet(f"background:{theme.OK if on else theme.BORDER};border-radius:3px;")
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            col = vbox(spacing=2)
            nm = label(str(t.get("name", "")))
            nm.setStyleSheet(f"color:{theme.TEXT};font-size:11.5px;font-weight:600;")
            col.addWidget(nm)
            for ef in t.get("effs", []):
                d = label(describe_effect(ef, self.s.state), "Muted")
                d.setStyleSheet(f"color:{theme.MUTED};font-size:10.5px;")
                col.addWidget(d)
            row.addLayout(col, 1)
            box.add_layout(row)
        self.equipped_lay.addWidget(box)

    # ------------------------------------------------------------------ 变更

    def _set_char(self, key: str, value: Any, chars: bool = False, rebuild: bool = False) -> None:
        if self.s.selected is None:
            return
        self.s.selected[key] = value
        self.s.touch(chars=chars)
        if rebuild:
            self.rebuild()

    def _set_eb(self, key: str, value: float) -> None:
        ch = self.s.selected
        if ch is None:
            return
        ch.setdefault("elemDmgBonus", st.def_eb())[key] = value
        self.s.touch()

    def _touch(self) -> None:
        self.s.touch()

    def _rebuild_soon(self) -> None:
        self.s.touch()
        self.rebuild()

    def _add_source(self, kind: str) -> None:
        ch = self.s.selected
        if ch is None or self.quick_table_mode:
            return
        ch.setdefault("dmgSrcs", []).append(st.new_dmg_source(kind))
        self.s.touch(editor=True)
        self.rebuild()

    def _remove_source(self, sid: str) -> None:
        ch = self.s.selected
        if ch is None:
            return
        ch["dmgSrcs"] = [d for d in ch.get("dmgSrcs", []) if d.get("id") != sid]
        self.s.touch(editor=True)
        self.rebuild()

    def _add_talent(self) -> None:
        ch = self.s.selected
        if ch is None:
            return
        ch.setdefault("talents", []).append(st.new_talent())
        self.s.touch(editor=True)
        self.rebuild()

    def _remove_talent(self, tid: str) -> None:
        ch = self.s.selected
        if ch is None:
            return
        ch["talents"] = [t for t in ch.get("talents", []) if t.get("id") != tid]
        self.s.touch(editor=True)
        self.rebuild()
