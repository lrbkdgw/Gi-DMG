"""快捷配置助手 + 武器库 / 圣遗物库（对应 HTML quickSetter / weaponLibModal / artifactLibModal）。

武器库与圣遗物库保存在 date/library/ 下，随存随写。
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QInputDialog, QMessageBox, QWidget)

from ...core import quickset as qsc, state as st
from ...core.constants import (QS_ASC_OPTS, QS_CIRCLET_OPTS, QS_GOBLET_OPTS, QS_SAND_OPTS,
                               QS_WEAPON_SUB_OPTS)
from .. import icons, theme, widgets as W
from ..effects import EffectList
from ..session import Session
from ..widgets import button, chip, clear_layout, hbox, icon_button, label, vbox
from .base import Modal

SUB_FIELDS = [("atk_pct", "攻击%"), ("hp_pct", "生命%"), ("def_pct", "防御%"),
              ("em", "精通"), ("cr", "暴击率"), ("cd", "暴击伤害"),
              ("atk_flat", "小攻击"), ("hp_flat", "小生命"), ("def_flat", "小防御")]
LEVEL_OPTS = [(str(v), str(v)) for v in (90, 80, 70, 60, 50, 40)]
RARITY_OPTS = [("5", "5星"), ("4", "4星"), ("3", "3星")]
PHASE_OPTS = [(str(p), f"{p}阶") for p in range(7)]


def _opts(pairs) -> List:
    return [(o["id"], o["n"]) for o in pairs]


def _mini(w: QWidget) -> QWidget:
    w.setStyleSheet("min-height:27px;font-size:11px;padding:0 7px;")
    return w


class TimedEffectGroup(QFrame):
    """武器天赋 / 圣遗物套装：名称 + 开关 + 生效区间 + 效果列表。"""

    changed = None  # 由外部赋值的回调

    def __init__(self, session: Session, item: Dict[str, Any], parent=None,
                 on_change: Optional[Callable[[], None]] = None,
                 on_remove: Optional[Callable[[], None]] = None,
                 name_key: str = "name"):
        super().__init__(parent)
        self.s = session
        self.item = item
        self.on_change = on_change or (lambda: None)
        self.setObjectName("TEG")
        self._border()
        lay = vbox(self, (10, 9, 10, 10), 8)

        head = hbox(spacing=6)
        name = W.TextField(str(item.get(name_key, "")))
        name.textEdited.connect(lambda t: self._set(name_key, t))
        head.addWidget(_mini(name), 1)
        tg = W.ToggleSwitch(bool(item.get("on", True)), scale=0.8)
        tg.toggled.connect(lambda v: self._set("on", v))
        head.addWidget(tg, 0, Qt.AlignmentFlag.AlignVCenter)
        if on_remove:
            head.addWidget(icon_button("trash-2", "删除", self, on_remove, size=13))
        lay.addLayout(head)

        if session.timeline_on:
            row = hbox(spacing=6)
            row.addWidget(label("生效区间", "Muted"))
            row.addStretch(1)
            row.addWidget(label("开始", "Muted"))
            f1 = W.NumField(item.get("startTime", 0), 0, decimals=2, width=58)
            f1.edited.connect(lambda v: self._set("startTime", v))
            row.addWidget(_mini(f1))
            row.addWidget(label("持续", "Muted"))
            dur = item.get("duration")
            f2 = W.NumField(20 if dur is None else dur, 20, decimals=2, width=58)
            f2.edited.connect(lambda v: self._set("duration", v))
            row.addWidget(_mini(f2))
            lay.addLayout(row)

        self.effects = EffectList(session.state, item.setdefault("effs", []), self)
        self.effects.changed.connect(self._on_eff)
        lay.addWidget(self.effects)

    def _border(self) -> None:
        bad = any(not st.eff_valid(ef) for ef in self.item.get("effs", []))
        color = theme.DANGER if bad else theme.BORDER
        self.setStyleSheet(f"QFrame#TEG {{ background:{theme.SURFACE}; border:1px solid {color};"
                           "border-radius:12px; }}")

    def _set(self, key: str, value: Any) -> None:
        self.item[key] = value
        self.on_change()

    def _on_eff(self) -> None:
        self._border()
        self.on_change()


class QuickSetterDialog(Modal):
    """① 角色基础属性 ② 武器 ③ 圣遗物 → 应用到角色面板。"""

    def __init__(self, parent, session: Session):
        super().__init__(parent, "快捷配置助手", "wand-sparkles", width=680, height=760)
        self.s = session
        self.ch = session.selected
        if self.ch is None:
            self.add(label("请先选择一个角色。", "Copy"))
            self.finish_body()
            return
        self.qs = qsc.migrate_quickset(self.ch.setdefault("qs", st.def_qs()))

        self.add(label(f"正在为「{self.ch.get('name','')}」推算面板。应用后会覆盖该角色的面板属性。",
                       "Copy", wrap=True))

        self.add(self._section_base())
        self.add(self._section_weapon())
        self.add(self._section_artifact())
        self.finish_body()

        self.add_button("取消", "", "", self.reject)
        self.add_button("应用所有配置（覆盖当前角色面板）", "check", "Primary", self._apply)

    # ------------------------------------------------------------------ ① 基础

    def _section_base(self) -> QWidget:
        card = W.SubCard(padding=14, spacing=10)
        card.add(label("① 角色基础属性", "FieldLabel"))
        base = self.qs["base"]

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(8)
        for i, (title, key) in enumerate((("基础生命", "hp"), ("基础攻击", "atk"), ("基础防御", "def"))):
            f = W.NumField(base.get(key, 0), 0, decimals=2)
            f.edited.connect(lambda v, k=key: self._set_base(k, v))
            g.addWidget(W.field(title, _mini(f)), 0, i)

        self.phase = W.Select(PHASE_OPTS, str(int(st.numz(base.get("ascPhase")))))
        self.phase.picked.connect(lambda v: self._set_asc("ascPhase", st.numz(v)))
        g.addWidget(W.field("突破等级", _mini(self.phase)), 1, 0)

        self.asc_type = W.Select(_opts(QS_ASC_OPTS), base.get("ascType", "none"))
        self.asc_type.picked.connect(lambda v: self._set_asc("ascType", v))
        g.addWidget(W.field("突破属性", _mini(self.asc_type)), 1, 1)

        self.asc_val = W.NumField(base.get("ascVal", 0), 0, decimals=2)
        self.asc_val.edited.connect(lambda v: self._set_base("ascVal", v))
        g.addWidget(W.field("突破数值(自动)", _mini(self.asc_val)), 1, 2)
        card.add_layout(g)
        return card

    def _set_base(self, key: str, value: float) -> None:
        self.qs["base"][key] = value

    def _set_asc(self, key: str, value: Any) -> None:
        self.qs["base"][key] = value
        qsc.infer_ascension(self.qs)
        self.asc_val.set_value(self.qs["base"]["ascVal"])

    # ------------------------------------------------------------------ ② 武器

    def _section_weapon(self) -> QWidget:
        card = W.SubCard(padding=14, spacing=10)
        head = hbox(spacing=8)
        head.addWidget(label("② 武器", "FieldLabel"), 1)
        head.addWidget(button("武器库", "package", "", card, self._open_weapon_lib))
        card.add_layout(head)
        w = self.qs["weapon"]

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(8)
        self.w_level = W.Select(LEVEL_OPTS, str(int(st.num(w.get("level"), 90))))
        self.w_level.picked.connect(lambda v: self._set_weapon("level", st.num(v, 90)))
        g.addWidget(W.field("等级", _mini(self.w_level)), 0, 0)

        self.w_rarity = W.Select(RARITY_OPTS, str(int(st.num(w.get("rarity"), 5))))
        self.w_rarity.picked.connect(self._on_rarity)
        g.addWidget(W.field("品质", _mini(self.w_rarity)), 0, 1)

        self.w_tier = W.Select(self._tier_opts(), str(int(st.numz(w.get("atkTier")))))
        self.w_tier.picked.connect(lambda v: self._set_weapon("atkTier", v))
        g.addWidget(W.field("白值档(90级)", _mini(self.w_tier)), 0, 2)

        self.w_atk = W.NumField(w.get("atk", 0), 0, decimals=2)
        self.w_atk.edited.connect(lambda v: self._set_weapon("atk", v, infer=False))
        g.addWidget(W.field("推理白值", _mini(self.w_atk)), 1, 0)

        self.w_sub = W.Select(_opts(QS_WEAPON_SUB_OPTS), w.get("subType", "none"))
        self.w_sub.picked.connect(lambda v: self._set_weapon("subType", v))
        g.addWidget(W.field("副词条类型", _mini(self.w_sub)), 1, 1)

        self.w_subval = W.NumField(w.get("subVal", 0), 0, decimals=2)
        self.w_subval.edited.connect(lambda v: self._set_weapon("subVal", v, infer=False))
        g.addWidget(W.field("推理副词条", _mini(self.w_subval)), 1, 2)
        card.add_layout(g)

        name = W.TextField(str(w.get("name", "")))
        name.textEdited.connect(lambda t: self._set_weapon("name", t, infer=False))
        card.add(W.field("武器名称", _mini(name)))

        row = hbox(spacing=8)
        row.addWidget(label("武器天赋", "FieldLabel"), 1)
        row.addWidget(icon_button("plus", "添加武器天赋", card, self._add_weapon_talent,
                                  theme.BLUE, 14, "AddBtn"))
        row.addWidget(button("存入武器库", "save", "", card, self._save_weapon))
        card.add_layout(row)

        self.w_tal_host = QWidget()
        self.w_tal_lay = vbox(self.w_tal_host, (0, 0, 0, 0), 8)
        card.add(self.w_tal_host)
        self._rebuild_weapon_talents()
        return card

    def _tier_opts(self):
        return [(str(t), str(t)) for t in qsc.weapon_tiers(self.qs["weapon"].get("rarity", 5))]

    def _on_rarity(self, value: str) -> None:
        self.qs["weapon"]["rarity"] = st.num(value, 5)
        tiers = qsc.weapon_tiers(value)
        self.qs["weapon"]["atkTier"] = str(tiers[0])
        self.w_tier.set_options(self._tier_opts(), str(tiers[0]))
        self._infer_weapon()

    def _set_weapon(self, key: str, value: Any, infer: bool = True) -> None:
        self.qs["weapon"][key] = value
        if infer and key in ("level", "rarity", "atkTier", "subType"):
            self._infer_weapon()

    def _infer_weapon(self) -> None:
        qsc.infer_weapon(self.qs)
        self.w_atk.set_value(self.qs["weapon"]["atk"])
        self.w_subval.set_value(self.qs["weapon"]["subVal"])

    def _rebuild_weapon_talents(self) -> None:
        clear_layout(self.w_tal_lay)
        talents = self.qs["weapon"].setdefault("talents", [])
        if not talents:
            lb = label("暂无武器天赋。", "Muted")
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11px;")
            self.w_tal_lay.addWidget(lb)
        for t in talents:
            g = TimedEffectGroup(self.s, t, self.w_tal_host, lambda: None,
                                 lambda tt=t: self._remove_weapon_talent(tt))
            self.w_tal_lay.addWidget(g)

    def _add_weapon_talent(self) -> None:
        self.qs["weapon"].setdefault("talents", []).append({
            "id": st.uid(), "on": True, "name": "武器天赋", "startTime": 0,
            "duration": 20, "effs": [st.new_effect()]})
        self._rebuild_weapon_talents()

    def _remove_weapon_talent(self, t: Dict[str, Any]) -> None:
        self.qs["weapon"]["talents"] = [x for x in self.qs["weapon"]["talents"] if x is not t]
        self._rebuild_weapon_talents()

    # ------------------------------------------------------------------ ③ 圣遗物

    def _section_artifact(self) -> QWidget:
        card = W.SubCard(padding=14, spacing=10)
        head = hbox(spacing=8)
        head.addWidget(label("③ 圣遗物", "FieldLabel"), 1)
        head.addWidget(button("圣遗物库", "gem", "", card, self._open_artifact_lib))
        card.add_layout(head)

        art = self.qs["artifact"]
        card.add(label("主词条", "Muted"))
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        for i, (slot, title, opts) in enumerate((("sand", "沙漏", QS_SAND_OPTS),
                                                 ("goblet", "杯子", QS_GOBLET_OPTS),
                                                 ("circlet", "头冠", QS_CIRCLET_OPTS))):
            sel = W.Select(_opts(opts), art["mains"].get(slot, "none"))
            sel.picked.connect(lambda v, s=slot: art["mains"].__setitem__(s, v))
            g.addWidget(W.field(title, _mini(sel)), 0, i)
        card.add_layout(g)

        card.add(label("副词条数量 (5星平均档)", "Muted"))
        g2 = QGridLayout()
        g2.setHorizontalSpacing(7)
        g2.setVerticalSpacing(7)
        subs = art.setdefault("subs", {})
        for i, (key, title) in enumerate(SUB_FIELDS):
            f = W.NumField(subs.get(key, 0), 0, decimals=2, allow_negative=False)
            f.edited.connect(lambda v, k=key: subs.__setitem__(k, v))
            g2.addWidget(W.field(title, _mini(f)), i // 3, i % 3)
        card.add_layout(g2)

        row = hbox(spacing=8)
        row.addWidget(label("套装天赋效果", "FieldLabel"), 1)
        row.addWidget(icon_button("plus", "添加套装", card, self._add_set, theme.BLUE, 14, "AddBtn"))
        row.addWidget(button("存入圣遗物库", "save", "", card, self._save_artifact))
        card.add_layout(row)

        self.set_host = QWidget()
        self.set_lay = vbox(self.set_host, (0, 0, 0, 0), 8)
        card.add(self.set_host)
        self._rebuild_sets()
        return card

    def _rebuild_sets(self) -> None:
        clear_layout(self.set_lay)
        sets = self.qs["artifact"].setdefault("sets", [])
        if not sets:
            lb = label("暂无套装效果。", "Muted")
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:11px;")
            self.set_lay.addWidget(lb)
        for s in sets:
            g = TimedEffectGroup(self.s, s, self.set_host, lambda: None,
                                 lambda ss=s: self._remove_set(ss))
            self.set_lay.addWidget(g)

    def _add_set(self) -> None:
        self.qs["artifact"].setdefault("sets", []).append({
            "name": "新套装", "on": True, "startTime": 0, "duration": 20,
            "effs": [st.new_effect()]})
        self._rebuild_sets()

    def _remove_set(self, s: Dict[str, Any]) -> None:
        self.qs["artifact"]["sets"] = [x for x in self.qs["artifact"]["sets"] if x is not s]
        self._rebuild_sets()

    # ------------------------------------------------------------------ 库

    def _save_weapon(self) -> None:
        name, ok = QInputDialog.getText(self, "存入武器库", "武器名称：",
                                        text=str(self.qs["weapon"].get("name", "武器")))
        if not ok:
            return
        entry = qsc.weapon_to_library_entry(self.qs)
        entry["name"] = name.strip() or "武器"
        lib = self.s.storage.load_weapon_lib()
        lib.insert(0, entry)
        self.s.storage.save_weapon_lib(lib)
        QMessageBox.information(self, "已保存", f"武器「{entry['name']}」已存入武器库。")

    def _save_artifact(self) -> None:
        name, ok = QInputDialog.getText(self, "存入圣遗物库", "配装名称：", text="圣遗物配装")
        if not ok:
            return
        entry = qsc.artifact_to_library_entry(self.qs, name.strip() or "圣遗物配装")
        lib = self.s.storage.load_artifact_lib()
        lib.insert(0, entry)
        self.s.storage.save_artifact_lib(lib)
        QMessageBox.information(self, "已保存", f"配装「{entry['name']}」已存入圣遗物库。")

    def _open_weapon_lib(self) -> None:
        dlg = LibraryDialog(self, self.s, "weapon")
        if dlg.exec() and dlg.picked is not None:
            entry = copy.deepcopy(dlg.picked)
            entry.pop("id", None)
            self.qs["weapon"] = {**st.def_qs()["weapon"], **entry}
            qsc.migrate_quickset(self.qs)
            self._reload()

    def _open_artifact_lib(self) -> None:
        dlg = LibraryDialog(self, self.s, "artifact")
        if dlg.exec() and dlg.picked is not None:
            entry = copy.deepcopy(dlg.picked)
            entry.pop("id", None)
            entry.pop("name", None)
            self.qs["artifact"] = {**st.def_qs()["artifact"], **entry}
            self._reload()

    def _reload(self) -> None:
        """从库里换了武器/圣遗物后整段重建。"""
        clear_layout(self.body)
        self.add(label(f"正在为「{self.ch.get('name','')}」推算面板。应用后会覆盖该角色的面板属性。",
                       "Copy", wrap=True))
        self.add(self._section_base())
        self.add(self._section_weapon())
        self.add(self._section_artifact())
        self.finish_body()

    # ------------------------------------------------------------------ 应用

    def _apply(self) -> None:
        qsc.apply_quickset(self.ch)
        self.s.touch(chars=True, editor=True, immediate=True)
        self.accept()


class LibraryDialog(Modal):
    """武器库 / 圣遗物库列表，支持选用与删除。"""

    def __init__(self, parent, session: Session, kind: str):
        title = "武器库" if kind == "weapon" else "圣遗物库"
        super().__init__(parent, title, "package" if kind == "weapon" else "gem",
                         width=520, height=520)
        self.s = session
        self.kind = kind
        self.picked: Optional[Dict[str, Any]] = None
        self.host = QWidget()
        self.host_lay = vbox(self.host, (0, 0, 0, 0), 7)
        self.add(self.host, 1)
        self.add_button("关闭", "", "", self.reject)
        self.reload()

    def _load(self) -> List[Dict[str, Any]]:
        return (self.s.storage.load_weapon_lib() if self.kind == "weapon"
                else self.s.storage.load_artifact_lib())

    def _save(self, lib) -> None:
        if self.kind == "weapon":
            self.s.storage.save_weapon_lib(lib)
        else:
            self.s.storage.save_artifact_lib(lib)

    def reload(self) -> None:
        clear_layout(self.host_lay)
        lib = self._load()
        if not lib:
            lb = label("库里还没有内容。在快捷配置助手中点「存入…」即可保存。", "Muted", wrap=True)
            lb.setStyleSheet(f"color:{theme.MUTED_SOFT};font-size:12px;padding:18px 4px;")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.host_lay.addWidget(lb)
        for entry in lib:
            self.host_lay.addWidget(self._row(entry))
        self.host_lay.addStretch(1)

    def _row(self, entry: Dict[str, Any]) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"QFrame {{ background:{theme.SURFACE_SUBTLE}; border-radius:12px; }}")
        lay = hbox(f, (12, 9, 10, 9), 10)
        col = vbox(spacing=3)
        t = label(str(entry.get("name", "未命名")))
        t.setStyleSheet(f"color:{theme.TEXT};font-size:12.5px;font-weight:700;")
        col.addWidget(t)
        if self.kind == "weapon":
            sub = (f"{int(st.num(entry.get('rarity'), 5))}星 · Lv.{int(st.num(entry.get('level'), 90))}"
                   f" · 白值 {st.numz(entry.get('atk')):g}")
        else:
            subs = entry.get("subs") or {}
            total = sum(st.numz(v) for v in subs.values())
            sub = f"{len(entry.get('sets') or [])} 个套装效果 · 副词条合计 {total:g} 条"
        col.addWidget(label(sub, "Muted"))
        lay.addLayout(col, 1)
        lay.addWidget(button("选用", "check", "Tonal", f, lambda: self._pick(entry)))
        lay.addWidget(icon_button("trash-2", "从库中删除", f, lambda: self._delete(entry)))
        return f

    def _pick(self, entry: Dict[str, Any]) -> None:
        self.picked = entry
        self.accept()

    def _delete(self, entry: Dict[str, Any]) -> None:
        self._save([e for e in self._load() if e.get("id") != entry.get("id")])
        self.reload()


def open_quick_setter(parent, session: Session) -> None:
    QuickSetterDialog(parent, session).exec()
