"""通用「效果」行编辑器，天赋 / 武器天赋 / 圣遗物套装共用。

对应 HTML 的 renderGenericEffRow() + bindGenericEff()。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QWidget

from ..core import state as st
from ..core.constants import ECAT
from . import theme, widgets as W
from .widgets import hbox, icon_button, label, vbox

PLACEHOLDER = "__placeholder__"


def cat_options(with_placeholder: bool = True) -> List[Tuple[str, str]]:
    opts: List[Tuple[str, str]] = [("", "选择分类")] if with_placeholder else []
    opts += [(k, v["n"]) for k, v in ECAT.items()]
    return opts


def type_options(cat: str, placeholder: str = "选择效果") -> List[Tuple[str, str]]:
    meta = ECAT.get(cat) or {}
    opts: List[Tuple[str, str]] = [("", placeholder)]
    opts += [(o["id"], o["n"]) for o in meta.get("opts", [])]
    return opts


def char_options(state: Dict[str, Any], include_placeholder: bool = True) -> List[Tuple[str, str]]:
    """只列启用角色（与 HTML charSelOpts 一致）。"""
    opts: List[Tuple[str, str]] = [("", "选择角色")] if include_placeholder else []
    opts += [(c["id"], str(c.get("name", ""))) for c in state.get("chars", []) if c.get("on")]
    return opts


def target_options(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    opts: List[Tuple[str, str]] = [("", "选择目标"), ("self", "自身"), ("team", "全队")]
    for c in state.get("chars", []):
        opts.append((f"char:{c['id']}", f"角色: {c.get('name','')}"))
        for d in c.get("dmgSrcs", []):
            opts.append((f"source:{d['id']}", f"伤害: {c.get('name','')}/{d.get('name','')}"))
    return opts


def feather_source_options(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    opts: List[Tuple[str, str]] = [("all", "所有来源")]
    for c in state.get("chars", []):
        for d in c.get("dmgSrcs", []):
            opts.append((f"source:{d['id']}", f"{c.get('name','')}/{d.get('name','')}"))
    return opts


class EffectRow(QFrame):
    """一条效果：分类 / 效果 / 目标 / 数值 / 删除。"""

    changed = Signal()          # 只是数值变了，重算即可
    structureChanged = Signal()  # 分类或目标变了，需要重建这一行
    removed = Signal()

    def __init__(self, state: Dict[str, Any], ef: Dict[str, Any], parent=None,
                 read_only: bool = False):
        super().__init__(parent)
        self.state = state
        self.ef = ef
        self.setObjectName("EffRow")
        self._apply_border()

        lay = hbox(self, (7, 5, 5, 5), 5)

        self.cat = W.Select(cat_options(), ef.get("cat", ""))
        self.cat.setFixedWidth(88)
        self.cat.picked.connect(self._on_cat)
        lay.addWidget(self.cat)

        self.type = W.Select(type_options(ef.get("cat", "")), ef.get("type", ""))
        self.type.picked.connect(self._on_type)
        lay.addWidget(self.type, 3)

        if ef.get("cat") == "feather":
            self.target = W.Select(feather_source_options(state), ef.get("featherSource", "all"))
            self.target.picked.connect(lambda v: self._set("featherSource", v))
            lay.addWidget(self.target, 4)
        elif st.is_enemy_global_eff(ef):
            tag = W.Pill("敌人", "#a35a55", "#faeef1")
            tag.setFixedHeight(26)
            tag.setMinimumWidth(56)
            lay.addWidget(tag, 2)
            self.target = None
        else:
            self.target = W.Select(target_options(state), ef.get("target", ""))
            self.target.picked.connect(self._on_target)
            lay.addWidget(self.target, 3)

        self.value = W.NumField(ef.get("value", 0), 0, decimals=3, width=74)
        self.value.edited.connect(lambda v: self._set("value", v, rebuild=False))
        lay.addWidget(self.value)

        self.del_btn = icon_button("x", "删除该效果", self, self.removed.emit, size=13)
        lay.addWidget(self.del_btn)

        for w in (self.cat, self.type, self.value):
            w.setStyleSheet("min-height:26px;font-size:11px;padding:0 7px;")
        if self.target is not None:
            self.target.setStyleSheet("min-height:26px;font-size:11px;padding:0 7px;")

        if read_only:
            for w in (self.cat, self.type, self.value, self.del_btn):
                w.setEnabled(False)
            if self.target is not None:
                self.target.setEnabled(False)

    # ------------------------------------------------------------------

    def _apply_border(self) -> None:
        ok = st.eff_valid(self.ef)
        color = theme.BORDER if ok else theme.DANGER
        bg = "#ffffff" if ok else "#fffafa"
        self.setStyleSheet(
            f"QFrame#EffRow {{ background:{bg}; border:1px solid {color}; border-radius:10px; }}")

    def _set(self, key: str, value: Any, rebuild: bool = True) -> None:
        self.ef[key] = value
        self._apply_border()
        self.changed.emit()

    def _on_cat(self, value: str) -> None:
        self.ef["cat"] = value
        opts = (ECAT.get(value) or {}).get("opts", [])
        self.ef["type"] = opts[0]["id"] if opts else ""
        if value == "feather" and not self.ef.get("featherSource"):
            self.ef["featherSource"] = "all"
        st.apply_base_type_default(self.ef)
        self.structureChanged.emit()

    def _on_type(self, value: str) -> None:
        self.ef["type"] = value
        st.apply_base_type_default(self.ef)
        self.structureChanged.emit()

    def _on_target(self, value: str) -> None:
        self.ef["target"] = value
        self._apply_border()
        self.structureChanged.emit()


class EffectList(QWidget):
    """一组效果行 + 「添加效果」按钮。"""

    changed = Signal()
    structureChanged = Signal()

    def __init__(self, state: Dict[str, Any], effs: List[Dict[str, Any]], parent=None,
                 read_only: bool = False, add_text: str = "+ 添加效果"):
        super().__init__(parent)
        self.state = state
        self.effs = effs
        self.read_only = read_only
        lay = vbox(self, (0, 0, 0, 0), 5)
        self.rows_host = QWidget(self)
        self.rows_lay = vbox(self.rows_host, (0, 0, 0, 0), 5)
        lay.addWidget(self.rows_host)

        if not read_only:
            row = hbox(spacing=6)
            self.add_btn = W.button(add_text, "circle-plus", "Link", self, self._add)
            row.addWidget(self.add_btn)
            row.addStretch(1)
            lay.addLayout(row)
        self.rebuild()

    def rebuild(self) -> None:
        W.clear_layout(self.rows_lay)
        for i, ef in enumerate(self.effs):
            row = EffectRow(self.state, ef, self.rows_host, self.read_only)
            row.changed.connect(self.changed.emit)
            row.structureChanged.connect(self._restructure)
            row.removed.connect(lambda idx=i: self._remove(idx))
            self.rows_lay.addWidget(row)

    def _restructure(self) -> None:
        self.rebuild()
        self.changed.emit()

    def _add(self) -> None:
        self.effs.append(st.new_effect())
        self.rebuild()
        self.changed.emit()

    def _remove(self, index: int) -> None:
        if 0 <= index < len(self.effs):
            self.effs.pop(index)
        self.rebuild()
        self.changed.emit()


def describe_effect(ef: Dict[str, Any], state: Dict[str, Any]) -> str:
    """把一条效果转成人类可读的短句，用于「已装备效果」概览。"""
    cat = ECAT.get(ef.get("cat", "")) or {}
    type_name = next((o["n"] for o in cat.get("opts", []) if o["id"] == ef.get("type")),
                     str(ef.get("type", "")))
    target = ef.get("target", "")
    if ef.get("cat") == "feather":
        src = ef.get("featherSource", "all")
        if src == "all":
            where = "所有来源"
        else:
            sid = src.split(":", 1)[-1]
            where = next((f"{c.get('name','')}/{d.get('name','')}"
                          for c in state.get("chars", []) for d in c.get("dmgSrcs", [])
                          if d.get("id") == sid), "来源")
        return f"{type_name} +{st.numz(ef.get('value')):g}（{where}）"
    if st.is_enemy_global_eff(ef):
        where = "敌人"
    elif target == "self":
        where = "自身"
    elif target == "team":
        where = "全队"
    elif target.startswith("char:"):
        cid = target.split(":", 1)[1]
        where = next((str(c.get("name", "")) for c in state.get("chars", [])
                      if c.get("id") == cid), "角色")
    elif target.startswith("source:"):
        sid = target.split(":", 1)[1]
        where = next((f"{c.get('name','')}/{d.get('name','')}"
                      for c in state.get("chars", []) for d in c.get("dmgSrcs", [])
                      if d.get("id") == sid), "来源")
    else:
        where = "未指定"
    val = st.numz(ef.get("value"))
    return f"{type_name} {'+' if val >= 0 else ''}{val:g} → {where}"
