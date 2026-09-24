"""快捷配置助手的推算逻辑（HTML: inferWeapon / inferAscension / applyStatType / applyQS）。

把「突破 + 武器 + 圣遗物词条」换算成角色面板数值，结果必须与 HTML 完全一致。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from .constants import (ART_MAIN_VALUE, ART_SUB_VALUE, ASC_MAX, ASC_MULT, EL_IDS,
                        WPN_ATK_FRAC, WPN_DATA, WPN_SUB_FRAC)
from .engine import jround
from .state import def_eb, def_qs, num, numz, r2, uid


def weapon_tiers(rarity: Any) -> List[int]:
    tbl = WPN_DATA.get(int(num(rarity, 5)), WPN_DATA[5])
    return sorted(tbl.keys(), reverse=True)


def lerp_table(table: Dict[int, float], lv: Any) -> float:
    """按等级在稀疏表里线性插值（HTML lerpTable）。"""
    level = num(lv, 90)
    if level in table:
        return table[int(level)]
    keys = sorted(table.keys())
    lo, hi = keys[0], keys[-1]
    for a, b in zip(keys, keys[1:]):
        if a <= level <= b:
            lo, hi = a, b
            break
    if hi == lo:
        return table[lo]
    return table[lo] + (table[hi] - table[lo]) * (level - lo) / (hi - lo)


def infer_weapon(qs: Dict[str, Any]) -> None:
    """按品质/白值档/等级推算武器攻击力与副词条。"""
    w = qs.setdefault("weapon", def_qs()["weapon"])
    rarity = int(num(w.get("rarity"), 5))
    level = num(w.get("level"), 90)
    tiers = weapon_tiers(rarity)
    tier = int(numz(w.get("atkTier")))
    if tier not in tiers:
        tier = tiers[0]
        w["atkTier"] = str(tier)
    data = WPN_DATA[rarity][tier]
    w["atk"] = jround(data["atk1"] + (tier - data["atk1"]) * lerp_table(WPN_ATK_FRAC, level))
    sub_max = data["sub"].get(w.get("subType"))
    w["subVal"] = round(sub_max * lerp_table(WPN_SUB_FRAC, level), 1) if sub_max is not None else 0


def infer_ascension(qs: Dict[str, Any]) -> None:
    """按突破阶数推算突破属性数值。"""
    base = qs.setdefault("base", def_qs()["base"])
    phase = int(max(0, min(6, num(base.get("ascPhase"), 0) if base.get("ascPhase") not in (0, "0") else 0)))
    if base.get("ascPhase") in (0, "0"):
        phase = 0
    base["ascVal"] = round((ASC_MAX.get(base.get("ascType"), 0) / 4) * ASC_MULT[phase], 1)


def apply_stat_type(ch: Dict[str, Any], stat_type: Any, value: float) -> None:
    """把一条词条加到角色面板上（HTML applyStatType）。"""
    if not stat_type or stat_type == "none" or not value:
        return
    mapping = {"atk_pct": "atkPct", "hp_pct": "hpPct", "def_pct": "defPct", "em": "em",
               "cr": "critRate", "cd": "critDMG", "atk_flat": "atkFlat",
               "hp_flat": "hpFlat", "def_flat": "defFlat"}
    key = mapping.get(stat_type)
    if key:
        ch[key] = numz(ch.get(key)) + value
        return
    if isinstance(stat_type, str) and stat_type.startswith("dmg_"):
        elem = stat_type[4:]
        eb = ch.setdefault("elemDmgBonus", def_eb())
        if elem in eb:
            eb[elem] = numz(eb.get(elem)) + value


def apply_quickset(ch: Dict[str, Any]) -> None:
    """把快捷配置写回角色面板（覆盖式，HTML applyQS）。"""
    qs = ch.setdefault("qs", def_qs())
    base = qs.setdefault("base", def_qs()["base"])
    weapon = qs.setdefault("weapon", def_qs()["weapon"])
    art = qs.setdefault("artifact", def_qs()["artifact"])

    if numz(base.get("hp")):
        ch["baseHP"] = numz(base["hp"])
    if numz(base.get("atk")):
        ch["baseAtk"] = numz(base["atk"])
    if numz(base.get("def")):
        ch["baseDef"] = numz(base["def"])

    ch["atkPct"] = 0
    ch["atkFlat"] = 311
    ch["hpPct"] = 0
    ch["hpFlat"] = 4780
    ch["defPct"] = 0
    ch["defFlat"] = 0
    ch["em"] = 0
    ch["critRate"] = 5
    ch["critDMG"] = 50
    eb = ch.setdefault("elemDmgBonus", def_eb())
    for e in EL_IDS:
        eb[e] = 0

    apply_stat_type(ch, base.get("ascType"), numz(base.get("ascVal")))
    if numz(weapon.get("atk")):
        ch["weaponAtk"] = numz(weapon["atk"])
    apply_stat_type(ch, weapon.get("subType"), numz(weapon.get("subVal")))

    for key, count in (art.get("subs") or {}).items():
        n = numz(count)
        if n and key in ART_SUB_VALUE:
            apply_stat_type(ch, key, n * ART_SUB_VALUE[key])

    mains = art.get("mains") or {}
    for slot in ("sand", "goblet", "circlet"):
        m = mains.get(slot)
        if not m or m == "none":
            continue
        if isinstance(m, str) and m.startswith("dmg_"):
            elem = m[4:]
            if elem in eb:
                eb[elem] = numz(eb.get(elem)) + (
                    ART_MAIN_VALUE["physical_dmg"] if elem == "physical" else ART_MAIN_VALUE["dmg"])
        elif m in ART_MAIN_VALUE:
            apply_stat_type(ch, m, ART_MAIN_VALUE[m])

    ch["talents"] = [t for t in ch.get("talents", [])
                     if not t.get("source") or t.get("source") == "manual"]

    for k in ("atkPct", "atkFlat", "hpPct", "hpFlat", "defPct", "defFlat",
              "em", "critRate", "critDMG", "allDmgBonus"):
        ch[k] = r2(numz(ch.get(k)))
    for e in EL_IDS:
        eb[e] = r2(numz(eb.get(e)))


def migrate_quickset(qs: Dict[str, Any]) -> Dict[str, Any]:
    """老配置兼容：把 weapon.effs 升级成 weapon.talents（HTML renderQS 里的迁移）。"""
    weapon = qs.setdefault("weapon", def_qs()["weapon"])
    if isinstance(weapon.get("effs"), list) and not isinstance(weapon.get("talents"), list):
        first = (weapon["effs"] or [{}])[0]
        weapon["talents"] = [{
            "id": uid(), "on": True, "name": "武器天赋",
            "startTime": numz(first.get("startTime")),
            "duration": 20 if first.get("duration") is None else numz(first.get("duration")),
            "effs": weapon["effs"],
        }]
        weapon["effs"] = []
    if not isinstance(weapon.get("talents"), list):
        weapon["talents"] = []
    art = qs.setdefault("artifact", def_qs()["artifact"])
    for s in art.setdefault("sets", []):
        s.setdefault("startTime", 0)
        s.setdefault("duration", 20)
    base = qs.setdefault("base", def_qs()["base"])
    base.setdefault("ascPhase", 6)
    if not numz(weapon.get("atk")):
        infer_weapon(qs)
    if not numz(base.get("ascVal")) and base.get("ascType") and base.get("ascType") != "none":
        infer_ascension(qs)
    return qs


def weapon_to_library_entry(qs: Dict[str, Any]) -> Dict[str, Any]:
    w = copy.deepcopy(qs.get("weapon") or {})
    w["id"] = uid()
    return w


def artifact_to_library_entry(qs: Dict[str, Any], name: str) -> Dict[str, Any]:
    art = copy.deepcopy(qs.get("artifact") or {})
    art["id"] = uid()
    art["name"] = name
    return art
