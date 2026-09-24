"""会话：把当前配置、结算结果和 date/ 持久化串起来。

界面各处只通过 Session 读写状态，改完调用 touch()，由它统一防抖重算并广播信号。
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from ..core import engine, state as st
from ..core.storage import Storage

CALC_DEBOUNCE_MS = 45
DRAFT_INTERVAL_MS = 30_000


class Session(QObject):
    """当前打开的配置。"""

    calcFinished = Signal()        # 结算完成，结果面板/时间轴刷新
    charsChanged = Signal()        # 角色增删改名/启用状态变化
    selectionChanged = Signal()    # 选中角色变化
    editorChanged = Signal()       # 当前角色的伤害来源/天赋结构变化
    dirtyChanged = Signal(bool)
    nameChanged = Signal(str)

    def __init__(self, storage: Storage, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.storage = storage
        self.config_name: str = ""
        self.state: Dict[str, Any] = st.normalize_state(st.def_state())
        self.result: Dict[str, Any] = engine.calc(self.state)
        self._dirty = False
        self._saved_snapshot = ""

        self._calc_timer = QTimer(self)
        self._calc_timer.setSingleShot(True)
        self._calc_timer.setInterval(CALC_DEBOUNCE_MS)
        self._calc_timer.timeout.connect(self.recalc)

        self._draft_timer = QTimer(self)
        self._draft_timer.setInterval(DRAFT_INTERVAL_MS)
        self._draft_timer.timeout.connect(self._autosave_draft)

    # -------------------------------------------------- 打开 / 保存

    def open(self, name: str, state: Optional[Dict[str, Any]] = None) -> None:
        self.config_name = name
        self.state = st.normalize_state(state if state is not None else self.storage.load_config(name))
        st.migrate_runtime(self.state)
        self._saved_snapshot = self._snapshot()
        self.set_dirty(False)
        self.recalc()
        self._draft_timer.start()
        self.nameChanged.emit(name)
        self.charsChanged.emit()
        self.selectionChanged.emit()

    def close(self) -> None:
        self._draft_timer.stop()
        self._calc_timer.stop()

    def save(self) -> None:
        self.recalc()
        self.storage.save_config(self.config_name, self.state, self.result.get("total", 0.0))
        self.storage.update_settings(lastConfig=self.config_name)
        self._saved_snapshot = self._snapshot()
        self.set_dirty(False)

    def discard(self) -> None:
        """不保存退出：丢弃草稿，磁盘上的配置保持原样。"""
        self.storage.clear_draft(self.config_name)
        self.set_dirty(False)

    def capture_history(self) -> None:
        self.storage.capture_cfg_history(self.state, self.result.get("total", 0.0), self.config_name)

    def rename(self, new_name: str) -> str:
        real = self.storage.rename_config(self.config_name, new_name) \
            if self.storage.config_exists(self.config_name) else self.storage.unique_name(new_name)
        self.config_name = real
        self.nameChanged.emit(real)
        return real

    def _snapshot(self) -> str:
        try:
            return json.dumps(st.make_config_snapshot(self.state), sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            return ""

    def _autosave_draft(self) -> None:
        if self._dirty and self.config_name:
            self.storage.save_draft(self.config_name, self.state)

    # -------------------------------------------------- 脏标记 / 重算

    @property
    def dirty(self) -> bool:
        return self._dirty

    def set_dirty(self, value: bool) -> None:
        value = bool(value)
        if value != self._dirty:
            self._dirty = value
            self.dirtyChanged.emit(value)

    def touch(self, *, chars: bool = False, editor: bool = False,
              selection: bool = False, immediate: bool = False) -> None:
        """状态被修改后调用。"""
        self.set_dirty(self._snapshot() != self._saved_snapshot)
        if chars:
            self.charsChanged.emit()
        if editor:
            self.editorChanged.emit()
        if selection:
            self.selectionChanged.emit()
        if immediate:
            self._calc_timer.stop()
            self.recalc()
        else:
            self._calc_timer.start()

    def recalc(self) -> None:
        self._calc_timer.stop()
        try:
            self.result = engine.calc(self.state)
        except Exception:  # 计算异常不应让界面崩溃
            self.result = {"total": 0.0, "dps": 0.0, "results": [], "panels": [],
                           "shares": {}, "detailShares": {"direct": {}, "feather": {}, "reaction": 0.0},
                           "fs": {}, "buf": {}, "reso": {}, "en": [], "inspectMap": {}, "sourceBuf": {}}
        self.calcFinished.emit()

    # -------------------------------------------------- 便捷访问

    @property
    def chars(self) -> List[Dict[str, Any]]:
        return self.state.setdefault("chars", [])

    @property
    def enabled_chars(self) -> List[Dict[str, Any]]:
        return [c for c in self.chars if c.get("on")]

    def char(self, char_id: Optional[str]) -> Optional[Dict[str, Any]]:
        return st.get_char(self.state, char_id)

    @property
    def selected(self) -> Optional[Dict[str, Any]]:
        return st.selected_char(self.state)

    def select(self, char_id: Optional[str]) -> None:
        if self.state.get("selId") != char_id:
            self.state["selId"] = char_id
            self.selectionChanged.emit()

    def add_char(self, template: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        c = copy.deepcopy(template) if template else st.def_char()
        c["id"] = st.uid()
        for d in c.get("dmgSrcs", []):
            d["id"] = st.uid()
        for t in c.get("talents", []):
            t["id"] = st.uid()
        if not template:
            c["name"] = f"角色 {len(self.chars) + 1}"
        self.chars.append(c)
        self.state["selId"] = c["id"]
        self.touch(chars=True, selection=True, immediate=True)
        return c

    def remove_char(self, char_id: str) -> None:
        self.state["chars"] = [c for c in self.chars if c.get("id") != char_id]
        if self.state.get("selId") == char_id:
            self.state["selId"] = self.chars[0]["id"] if self.chars else None
        self.touch(chars=True, selection=True, editor=True, immediate=True)

    def duplicate_char(self, char_id: str) -> Optional[Dict[str, Any]]:
        src = self.char(char_id)
        if not src:
            return None
        c = copy.deepcopy(src)
        c["id"] = st.uid()
        c["name"] = f"{src.get('name', '角色')} 副本"
        for d in c.get("dmgSrcs", []):
            d["id"] = st.uid()
        for t in c.get("talents", []):
            t["id"] = st.uid()
        self.chars.insert(self.chars.index(src) + 1, c)
        self.state["selId"] = c["id"]
        self.touch(chars=True, selection=True, immediate=True)
        return c

    def reset_config(self) -> None:
        """清空所有角色与基准值（对应 HTML「更多 → 重置配置」）。"""
        self.state["chars"] = []
        self.state["selId"] = None
        self.state["baselines"] = []
        self.touch(chars=True, selection=True, editor=True, immediate=True)

    # -------------------------------------------------- 基准值

    @property
    def baselines(self) -> List[Dict[str, Any]]:
        return self.state.setdefault("baselines", [])

    def add_baseline(self, name: str) -> Dict[str, Any]:
        rec = {"id": st.uid(), "name": name, "val": float(self.result.get("total", 0.0)),
               "config": st.make_config_snapshot(self.state)}
        self.baselines.append(rec)
        self.touch()
        return rec

    def remove_baseline(self, bid: str) -> None:
        self.state["baselines"] = [b for b in self.baselines if b.get("id") != bid]
        self.touch()

    # -------------------------------------------------- 全队总览

    def resonances(self) -> List[Dict[str, Any]]:
        """元素共鸣（与 HTML rReso() 一致）。"""
        counts: Dict[str, int] = {}
        for c in self.enabled_chars:
            counts[c.get("element", "")] = counts.get(c.get("element", ""), 0) + 1
        out: List[Dict[str, Any]] = []
        if counts.get("pyro", 0) >= 2:
            out.append({"id": "pyro", "text": "热诚之火·攻击力+25%"})
        if counts.get("hydro", 0) >= 2:
            out.append({"id": "hydro", "text": "交织之水·生命值+25%"})
        if counts.get("cryo", 0) >= 2:
            out.append({"id": "cryo", "text": "粉碎之冰·暴击率+15%(条件)"})
        if counts.get("dendro", 0) >= 2:
            out.append({"id": "dendro", "text": "蔓生之草·精通+50"})
        if counts.get("geo", 0) >= 2:
            out.append({"id": "geo", "text": "坚定之岩·伤害+15%"})
        if len(counts) >= 4:
            out.append({"ids": list(counts.keys())[:4], "text": "交织之护·全抗+15%"})
        return out

    @property
    def rotation(self) -> float:
        return max(1.0, st.num(self.state.get("rotationDuration"), 20))

    @property
    def timeline_on(self) -> bool:
        return bool(self.state.get("timelineEnabled"))

    @property
    def share_on(self) -> bool:
        return bool(self.state.get("dmgShareEnabled"))
