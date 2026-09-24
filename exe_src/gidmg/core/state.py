"""配置状态模型。

结构与 HTML 版完全一致（纯 dict + JSON），因此 HTML 导出的 `genshin-dmg.json`
可以直接在 EXE 中打开，反之亦然。
"""

from __future__ import annotations

import copy
import random
import string
from typing import Any, Dict, Iterable, List, Optional

from .constants import EL, EL_IDS, ECAT, BASE_TYPES

_UID_ALPHABET = string.digits + string.ascii_lowercase


def uid() -> str:
    """等价于 JS 的 Math.random().toString(36).slice(2,8)。"""
    return "".join(random.choice(_UID_ALPHABET) for _ in range(6))


def num(value: Any, default: float = 0.0) -> float:
    """等价于 JS 的 `+x || default`（0 / NaN / None / 空串都回落到 default）。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if f != f or f == 0:  # NaN 或 0
        return float(default)
    return f


def numz(value: Any) -> float:
    """等价于 JS 的 `+x || 0`。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if f != f else f


def r2(x: Any) -> float:
    """等价于 JS 的 r2()：四舍五入到两位小数。"""
    v = numz(x)
    return round(v * 100) / 100


def def_eb() -> Dict[str, float]:
    return {e: 0.0 for e in EL_IDS}


def def_qs() -> Dict[str, Any]:
    return {
        "base": {"hp": 0, "atk": 0, "def": 0, "ascType": "none", "ascPhase": 6, "ascVal": 0},
        "weapon": {
            "level": 90, "rarity": 5, "atkTier": "542", "atk": 0,
            "subType": "none", "subVal": 0, "name": "武器效果", "talents": [],
        },
        "artifact": {
            "subs": {"atk_pct": 0, "hp_pct": 0, "def_pct": 0, "em": 0, "cr": 0, "cd": 0,
                     "atk_flat": 0, "hp_flat": 0, "def_flat": 0},
            "mains": {"sand": "none", "goblet": "none", "circlet": "none"},
            "sets": [],
        },
    }


def def_char(element: str = "pyro") -> Dict[str, Any]:
    return {
        "id": uid(), "on": True, "name": "新角色", "lv": 90, "element": element,
        "baseAtk": 300, "weaponAtk": 510, "atkPct": 0, "atkFlat": 0,
        "baseDef": 600, "defPct": 0, "defFlat": 0,
        "baseHP": 10000, "hpPct": 0, "hpFlat": 0,
        "em": 0, "critRate": 5, "critDMG": 50, "allDmgBonus": 0,
        "elemDmgBonus": def_eb(), "dmgSrcs": [], "talents": [], "qs": def_qs(),
    }


def def_state() -> Dict[str, Any]:
    return {
        "timelineEnabled": True,
        "dmgShareEnabled": False,
        "rotationDuration": 20,
        "enemy": {"level": 93, "res": {e: 10 for e in EL_IDS}},
        "chars": [],
        "selId": None,
        "baselines": [],
        "baselineMode": "a",
    }


def new_effect() -> Dict[str, Any]:
    return {"cat": "", "type": "", "target": "", "value": 0}


def new_talent(name: str = "新天赋") -> Dict[str, Any]:
    return {
        "id": uid(), "on": True, "source": "manual", "name": name,
        "startTime": 0, "duration": 20, "isPermanent": False, "effs": [new_effect()],
    }


def new_dmg_source(kind: str) -> Dict[str, Any]:
    base = {"id": uid(), "on": True, "timingMode": "instant", "startTime": 0, "duration": 0}
    if kind == "normal":
        base.update({"type": "normal", "name": "新伤害", "stat": "", "mult": 100, "element": "",
                     "dmgType": "", "reaction": "", "triggerCharId": "", "statCharId": ""})
    elif kind == "trans":
        base.update({"type": "trans", "name": "新剧变", "transType": "", "triggerCount": 1,
                     "triggerCharId": "", "statCharId": ""})
    elif kind == "special_direct":
        base.update({"type": "special_direct", "name": "新特殊直伤", "specType": "", "stat": "",
                     "mult": 100, "triggerCharId": "", "statCharId": "", "starStacks": 1})
    else:
        base.update({"type": "special_reaction", "name": "新特殊反应", "specType": "",
                     "triggerCount": 1, "triggerCharId": "", "statCharId": "", "contribs": []})
    return base


# ------------------------------------------------------------------ 归一化

def normalize_state(raw: Any) -> Dict[str, Any]:
    """对应 HTML 的 normalizeState()：校验并补齐缺失字段。"""
    if not isinstance(raw, dict):
        raise ValueError("配置文件根节点必须是对象")
    raw = copy.deepcopy(raw)
    base_res = {e: 10 for e in EL_IDS}

    raw["timelineEnabled"] = raw.get("timelineEnabled") is not False
    raw["dmgShareEnabled"] = bool(raw.get("dmgShareEnabled"))
    raw["rotationDuration"] = max(1.0, num(raw.get("rotationDuration"), 20))

    enemy = raw.get("enemy")
    if not isinstance(enemy, dict):
        enemy = {}
    enemy["level"] = max(1.0, num(enemy.get("level"), 93))
    res = dict(base_res)
    if isinstance(enemy.get("res"), dict):
        res.update(enemy["res"])
    enemy["res"] = {k: numz(res.get(k)) for k in base_res}
    raw["enemy"] = enemy

    chars = raw.get("chars")
    raw["chars"] = [c for c in chars if isinstance(c, dict)] if isinstance(chars, list) else []

    used: set = set()
    for c in raw["chars"]:
        if not isinstance(c.get("id"), str) or not c["id"] or c["id"] in used:
            c["id"] = uid()
        used.add(c["id"])
        c["name"] = str(c.get("name", "新角色") if c.get("name") is not None else "新角色")
        c["on"] = c.get("on") is not False
        c["lv"] = max(1.0, num(c.get("lv"), 90))
        c["element"] = c["element"] if c.get("element") in EL_IDS else "pyro"
        eb = def_eb()
        if isinstance(c.get("elemDmgBonus"), dict):
            eb.update(c["elemDmgBonus"])
        c["elemDmgBonus"] = eb
        c["dmgSrcs"] = [d for d in c.get("dmgSrcs", []) if isinstance(d, dict)] \
            if isinstance(c.get("dmgSrcs"), list) else []
        c["talents"] = [t for t in c.get("talents", []) if isinstance(t, dict)] \
            if isinstance(c.get("talents"), list) else []
        if not isinstance(c.get("qs"), dict):
            c["qs"] = def_qs()
        qs = c["qs"]
        # v2.1.5：把旧版扁平的 weapon.effs 迁移为共享时间窗的武器天赋
        weapon = qs.get("weapon")
        if isinstance(weapon, dict):
            if isinstance(weapon.get("effs"), list) and not isinstance(weapon.get("talents"), list):
                first = weapon["effs"][0] if weapon["effs"] else {}
                weapon["talents"] = [{
                    "id": uid(), "on": True, "name": "武器天赋",
                    "startTime": numz(first.get("startTime")),
                    "duration": 20 if first.get("duration") is None else numz(first.get("duration")),
                    "effs": weapon["effs"],
                }]
                weapon["effs"] = []
            if not isinstance(weapon.get("talents"), list):
                weapon["talents"] = []
        artifact = qs.get("artifact")
        if isinstance(artifact, dict):
            for s in artifact.get("sets", []) or []:
                if not isinstance(s, dict):
                    continue
                s.setdefault("startTime", 0)
                s.setdefault("duration", 20)

    baselines = raw.get("baselines")
    raw["baselines"] = [b for b in baselines if isinstance(b, dict)] if isinstance(baselines, list) else []
    raw["baselineMode"] = "b" if raw.get("baselineMode") == "b" else "a"
    if not any(c["id"] == raw.get("selId") for c in raw["chars"]):
        raw["selId"] = raw["chars"][0]["id"] if raw["chars"] else None
    return raw


def migrate_runtime(state: Dict[str, Any]) -> None:
    """对应 HTML renderAll() 开头的运行期兜底与迁移。"""
    for c in state.get("chars", []):
        if not c.get("qs"):
            c["qs"] = def_qs()
        if not c.get("elemDmgBonus"):
            c["elemDmgBonus"] = def_eb()
        c.setdefault("dmgSrcs", [])
        c.setdefault("talents", [])
        for t in c["talents"]:
            if not t.get("source"):
                t["source"] = "manual"
            if not t.get("effs"):
                t["effs"] = []
            for ef in t["effs"]:
                if ef.get("cat") == "source":
                    ef["cat"] = "dmgType"
        extra: List[Dict[str, Any]] = []
        for d in c["dmgSrcs"]:
            if d.get("type") == "special_reaction" and d.get("contribs") is None:
                d["contribs"] = []
            if d.get("type") == "normal" and d.get("reaction") in ("aggravate", "spread"):
                q_type = d["reaction"]
                d["reaction"] = "none"
                extra.append({
                    "id": uid(), "on": d.get("on", True), "type": "trans",
                    "name": "蔓激化" if q_type == "spread" else "超激化",
                    "transType": q_type, "triggerCount": 1,
                    "triggerCharId": d.get("triggerCharId"), "statCharId": d.get("statCharId"),
                    "timingMode": "instant", "startTime": 0, "duration": 0,
                })
        c["dmgSrcs"].extend(extra)


# ------------------------------------------------------------------ 校验

def is_enemy_global_eff(ef: Dict[str, Any]) -> bool:
    return ef.get("cat") == "resShred" or (ef.get("cat") == "defense" and ef.get("type") == "def_shred")


def eff_valid(ef: Optional[Dict[str, Any]]) -> bool:
    if not ef:
        return False
    return bool(ef.get("cat") and ef.get("type")
                and (ef.get("cat") == "feather" or is_enemy_global_eff(ef) or ef.get("target")))


def talent_valid(t: Dict[str, Any]) -> bool:
    return all(eff_valid(ef) for ef in (t.get("effs") or []))


def apply_base_type_default(ef: Dict[str, Any]) -> None:
    if ef and ef.get("type") in BASE_TYPES and not ef.get("target"):
        ef["target"] = "team"


def dmg_source_valid(d: Dict[str, Any]) -> bool:
    t = d.get("type")
    if t == "normal":
        return bool(d.get("stat") and d.get("element") and d.get("dmgType") and d.get("reaction"))
    if t == "trans":
        return bool(d.get("transType"))
    if t == "special_direct":
        return bool(d.get("specType") and d.get("stat"))
    if t == "special_reaction":
        return not (not d.get("specType") or (not d.get("triggerCharId") and not (d.get("contribs") or [])))
    return True


def dmg_source_incomplete(d: Dict[str, Any]) -> bool:
    from .constants import get_spec_meta
    if not dmg_source_valid(d):
        return True
    t = d.get("type")
    if t in ("normal", "special_direct"):
        return not (d.get("triggerCharId") and d.get("statCharId"))
    if t == "trans":
        return not d.get("triggerCharId")
    if t == "special_reaction":
        if not (d.get("contribs") or []):
            return True
        meta = get_spec_meta(d.get("specType"))
        if meta and meta.get("cryoChoice") and not d.get("starSwirlCryoMult"):
            return True
    return False


# ------------------------------------------------------------------ 便捷访问

def get_char(state: Dict[str, Any], char_id: Optional[str]) -> Optional[Dict[str, Any]]:
    for c in state.get("chars", []):
        if c.get("id") == char_id:
            return c
    return None


def selected_char(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_char(state, state.get("selId"))


def enabled_chars(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in state.get("chars", []) if c.get("on")]


def all_sources(state: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for c in state.get("chars", []):
        for d in c.get("dmgSrcs", []) or []:
            yield c, d


def final_atk(c: Dict[str, Any]) -> float:
    return (numz(c.get("baseAtk")) + numz(c.get("weaponAtk"))) * (1 + numz(c.get("atkPct")) / 100) + numz(c.get("atkFlat"))


def final_def(c: Dict[str, Any]) -> float:
    return numz(c.get("baseDef")) * (1 + numz(c.get("defPct")) / 100) + numz(c.get("defFlat"))


def final_hp(c: Dict[str, Any]) -> float:
    return numz(c.get("baseHP")) * (1 + numz(c.get("hpPct")) / 100) + numz(c.get("hpFlat"))


def make_config_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy({
        "timelineEnabled": state.get("timelineEnabled"),
        "dmgShareEnabled": bool(state.get("dmgShareEnabled")),
        "rotationDuration": state.get("rotationDuration"),
        "enemy": state.get("enemy"),
        "chars": state.get("chars"),
        "selId": state.get("selId"),
        "baselineMode": state.get("baselineMode", "a"),
    })


# ------------------------------------------------------------------ 预设角色

PRESETS: Dict[str, Dict[str, Any]] = {
    "hutao": {
        "name": "胡桃", "el": "pyro", "bAtk": 106, "wAtk": 510, "bDef": 876, "bHP": 15552,
        "hPct": 116.3, "hFlat": 4780, "em": 210, "cr": 72, "cd": 210, "eb": {"pyro": 61.6},
        "dm": [{"on": True, "type": "normal", "name": "重击·蝶引来生", "stat": "atk", "mult": 243,
                "element": "pyro", "dmgType": "CA", "reaction": "vape",
                "timingMode": "uniform_snapshot", "startTime": 2, "duration": 9}],
    },
    "yelan": {
        "name": "夜兰", "el": "hydro", "bAtk": 244, "wAtk": 542, "aFlat": 311, "bDef": 548,
        "bHP": 14450, "hPct": 91.2, "hFlat": 4780, "em": 80, "cr": 68, "cd": 195,
        "eb": {"hydro": 58},
        "dm": [
            {"on": True, "type": "normal", "name": "破局矢", "stat": "hp", "mult": 28.5,
             "element": "hydro", "dmgType": "CA", "reaction": "none",
             "timingMode": "instant", "startTime": 0, "duration": 0},
            {"on": True, "type": "normal", "name": "玄掷玲珑(连携)", "stat": "hp", "mult": 8.7,
             "element": "hydro", "dmgType": "Q", "reaction": "none",
             "timingMode": "uniform_dynamic", "startTime": 1, "duration": 15},
        ],
    },
    "nahida": {
        "name": "纳西妲", "el": "dendro", "bAtk": 299, "wAtk": 510, "aPct": 14, "aFlat": 311,
        "bDef": 630, "bHP": 10360, "hFlat": 4780, "em": 820, "cr": 45, "cd": 135,
        "eb": {"dendro": 46.6},
        "dm": [
            {"on": True, "type": "normal", "name": "灭净三业", "stat": "atk", "mult": 185,
             "element": "dendro", "dmgType": "E", "reaction": "none",
             "timingMode": "uniform_dynamic", "startTime": 1, "duration": 14},
            {"on": True, "type": "trans", "name": "蔓激化", "transType": "spread", "triggerCount": 1,
             "timingMode": "uniform_dynamic", "startTime": 1, "duration": 14},
        ],
    },
    "raiden": {
        "name": "雷电将军", "el": "electro", "bAtk": 337, "wAtk": 608, "aPct": 49.6, "aFlat": 311,
        "bDef": 789, "bHP": 12907, "hFlat": 4780, "em": 80, "cr": 65, "cd": 155,
        "eb": {"electro": 66},
        "dm": [
            {"on": True, "type": "normal", "name": "梦想一刀", "stat": "atk", "mult": 720,
             "element": "electro", "dmgType": "Q", "reaction": "none",
             "timingMode": "instant", "startTime": 3, "duration": 0},
            {"on": True, "type": "trans", "name": "超激化", "transType": "aggravate", "triggerCount": 1,
             "timingMode": "instant", "startTime": 3, "duration": 0},
        ],
    },
}


def build_preset(key: str) -> Optional[Dict[str, Any]]:
    p = PRESETS.get(key)
    if not p:
        return None
    c = def_char(p["el"])
    c["name"] = p["name"]
    c["baseAtk"] = p["bAtk"]
    c["weaponAtk"] = p["wAtk"]
    c["atkPct"] = p.get("aPct", 0)
    c["atkFlat"] = p.get("aFlat", 0)
    c["baseDef"] = p["bDef"]
    c["defPct"] = p.get("dPct", 0)
    c["defFlat"] = p.get("dFlat", 0)
    c["baseHP"] = p["bHP"]
    c["hpPct"] = p.get("hPct", 0)
    c["hpFlat"] = p.get("hFlat", 0)
    c["em"] = p["em"]
    c["critRate"] = p["cr"]
    c["critDMG"] = p["cd"]
    c["allDmgBonus"] = 0
    eb = def_eb()
    eb.update(p.get("eb", {}))
    c["elemDmgBonus"] = eb
    srcs = []
    for d in p["dm"]:
        nd = dict(d)
        nd["id"] = uid()
        nd["triggerCharId"] = c["id"]
        nd["statCharId"] = c["id"]
        srcs.append(nd)
    c["dmgSrcs"] = srcs
    return c
