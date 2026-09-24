"""伤害结算引擎。

逐行移植自 `Gi DMG v2.1.9.html` 的 evaluateStateAt / computeSingleHit / calc，
数值结果与 HTML 版一致（见 exe_src/tests/test_engine_parity.py 的对拍测试）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    EL_IDS, LV_COEFF, TRANS_BY_ID, get_spec_meta,
)
from .state import (
    def_eb, def_qs, dmg_source_valid, num, numz, talent_valid,
)


def jround(x: float) -> int:
    """JS Math.round 语义：四舍五入且 .5 向 +∞ 取整。"""
    if x != x or x in (float("inf"), float("-inf")):
        return 0
    return int(math.floor(x + 0.5))


def level_coeff(lv: Any) -> float:
    lv = numz(lv)
    if lv in LV_COEFF:
        return LV_COEFF[lv]
    ilv = int(lv)
    if ilv == lv and ilv in LV_COEFF:
        return LV_COEFF[ilv]
    keys = sorted(LV_COEFF)
    lo, hi = keys[0], keys[-1]
    for i in range(len(keys) - 1):
        if keys[i] <= lv <= keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            break
    return LV_COEFF[lo] + (LV_COEFF[hi] - LV_COEFF[lo]) * ((lv - lo) / (hi - lo))


def get_star_stacks(d: Dict[str, Any]) -> float:
    if d.get("starStacks") is not None:
        return numz(d.get("starStacks"))
    if d.get("starBase") is not None:
        base = numz(d.get("starBase"))
        return 0 if base <= 1 else jround((base - 1.45) / 0.05) + 1
    return 1


def star_coeff_from_stacks(n: float) -> float:
    return 1.00 if n <= 0 else 1.45 + 0.05 * (n - 1)


def get_star_base_mult(d: Dict[str, Any], extra: float = 0.0) -> float:
    return star_coeff_from_stacks(get_star_stacks(d) + (extra or 0))


# ------------------------------------------------------------------ Buff 容器

def _make_char_buff() -> Dict[str, Any]:
    return {
        "baseAtk": 0.0, "baseDef": 0.0, "baseHP": 0.0, "atkFlat": 0.0, "atkPct": 0.0,
        "defFlat": 0.0, "defPct": 0.0, "hpFlat": 0.0, "hpPct": 0.0, "emFlat": 0.0,
        "critRate": 0.0, "critDMG": 0.0,
        "dNA": 0.0, "dCA": 0.0, "dPA": 0.0, "dE": 0.0, "dQ": 0.0, "dAll": 0.0,
        "dElem": def_eb(), "ampBonus": 0.0,
        "transBonus": {"aggravate": 0.0, "spread": 0.0, "overloaded": 0.0, "superconduct": 0.0,
                       "electrocharged": 0.0, "swirl": 0.0, "shattered": 0.0, "bloom": 0.0,
                       "hyperbloom": 0.0, "burgeon": 0.0, "burning": 0.0},
        "lunarAll": 0.0, "lunarDirect": 0.0, "lunarReaction": 0.0, "lunarAscend": 0.0,
        "lunarBase": 0.0, "lunarBaseType": {"charged": 0.0, "bloom": 0.0, "crystal": 0.0},
        "lunarType": {"charged": 0.0, "bloom": 0.0, "crystal": 0.0},
        "specAll": 0.0, "specDirect": 0.0, "specReaction": 0.0, "specAscend": 0.0, "specBonus": {},
        "starAll": 0.0, "starBonus": 0.0, "starAscend": 0.0, "starAscends": [], "starStacks": 0.0,
        "starSdBonus": 0.0, "starBase": 0.0, "starBaseSC": 0.0, "starBaseSD": 0.0, "defIgnore": 0.0,
    }


def make_source_buff() -> Dict[str, Any]:
    return {
        "defIgnore": 0.0, "resShred": def_eb(), "sourceDmgBonus": 0.0, "finalMults": [],
        "dNA": 0.0, "dCA": 0.0, "dPA": 0.0, "dE": 0.0, "dQ": 0.0, "dAll": 0.0,
        "dElem": def_eb(), "ampBonus": 0.0,
        "transBonus": {"aggravate": 0.0, "spread": 0.0, "overloaded": 0.0, "superconduct": 0.0,
                       "electrocharged": 0.0, "swirl": 0.0, "shattered": 0.0, "bloom": 0.0,
                       "hyperbloom": 0.0, "burgeon": 0.0, "burning": 0.0},
        "lunarAll": 0.0, "lunarDirect": 0.0, "lunarReaction": 0.0, "lunarBase": 0.0,
        "lunarBaseType": {"charged": 0.0, "bloom": 0.0, "crystal": 0.0},
        "lunarType": {"charged": 0.0, "bloom": 0.0, "crystal": 0.0},
        "specAll": 0.0, "specDirect": 0.0, "specReaction": 0.0, "specBonus": {},
        "starAll": 0.0, "starBonus": 0.0, "starAscends": [], "starStacks": 0.0,
        "starSdBonus": 0.0, "starBase": 0.0, "starBaseSC": 0.0, "starBaseSD": 0.0,
        "specAscend": 0.0, "defShred": 0.0,
    }


_DEFAULT_FS = {"atk": 0.0, "def": 0.0, "hp": 0.0, "em": 0.0, "cr": 5.0, "cd": 50.0}


# ------------------------------------------------------------------ 天赋

def equipment_talents(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """武器 / 圣遗物天赋：一条天赋共享起止时间，展开为每个效果一条。"""
    qs = c.get("qs") or def_qs()
    out: List[Dict[str, Any]] = []

    def eq_dur(t: Dict[str, Any]) -> float:
        return 20.0 if t.get("duration") is None else numz(t.get("duration"))

    def add(lst, source, id_prefix):
        for i, t in enumerate(lst or []):
            if t.get("on") is False:
                continue
            for j, ef in enumerate(t.get("effs") or []):
                out.append({
                    "id": f"{id_prefix}{i}_{j}", "on": True, "source": source,
                    "name": f"{t.get('name') or ('天赋 ' + str(i + 1))} · {j + 1}",
                    "isPermanent": False, "startTime": numz(t.get("startTime")),
                    "duration": eq_dur(t), "effs": [ef],
                })

    add((qs.get("weapon") or {}).get("talents"), "weapon", "equip_weapon_" + str(c.get("id")))
    add((qs.get("artifact") or {}).get("sets"), "artifact", "equip_art_" + str(c.get("id")))
    return out


def active_talents(state: Dict[str, Any], c: Dict[str, Any], at_time: Optional[float] = None) -> List[Dict[str, Any]]:
    manual = [t for t in (c.get("talents") or [])
              if t.get("on") and (not t.get("source") or t.get("source") == "manual") and talent_valid(t)]
    all_t = manual + [t for t in equipment_talents(c) if talent_valid(t)]
    if not state.get("timelineEnabled") or at_time is None:
        return all_t
    rot = max(1.0, num(state.get("rotationDuration"), 20))
    t_norm = ((at_time % rot) + rot) % rot
    out = []
    for t in all_t:
        if t.get("isPermanent"):
            out.append(t)
            continue
        dur = numz(t.get("duration"))
        if dur <= 0:
            continue
        if dur >= rot:
            out.append(t)
            continue
        ts = ((numz(t.get("startTime")) % rot) + rot) % rot
        te = ts + dur
        if te <= rot:
            if ts <= t_norm <= te:
                out.append(t)
        else:
            if t_norm >= ts or t_norm <= (te % rot):
                out.append(t)
    return out


def _char_targets(ef: Dict[str, Any], owner: Dict[str, Any], en: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    t = ef.get("target") or "self"
    if t == "team":
        return en
    if t == "self":
        return [owner]
    if t.startswith("char:"):
        cid = t[5:]
        return [c for c in en if c.get("id") == cid]
    return []


def _source_targets(ef: Dict[str, Any], owner: Dict[str, Any], en: List[Dict[str, Any]],
                    source_buf: Dict[str, Any]) -> List[Dict[str, Any]]:
    t = ef.get("target") or "self"
    srcs: List[Dict[str, Any]] = []
    if t == "team":
        for c in en:
            srcs.extend(c.get("dmgSrcs") or [])
    elif t == "self":
        srcs = list(owner.get("dmgSrcs") or [])
    elif t.startswith("char:"):
        cid = t[5:]
        for c in en:
            if c.get("id") == cid:
                srcs = list(c.get("dmgSrcs") or [])
                break
    elif t.startswith("source:"):
        sid = t[7:]
        for c in en:
            for d in c.get("dmgSrcs") or []:
                if d.get("id") == sid:
                    srcs.append(d)
    out = []
    for d in srcs:
        sb = source_buf.get(d.get("id"))
        if sb:
            out.append(sb)
    return out


def base_zone_for(bb: Optional[Dict[str, Any]], ssb: Optional[Dict[str, Any]], meta: Dict[str, Any]) -> float:
    bb = bb or {}
    ssb = ssb or {}
    if meta.get("star"):
        z = numz(bb.get("starBase")) + numz(ssb.get("starBase"))
        if meta.get("id") == "star_sc_direct":
            z += numz(bb.get("starBaseSC")) + numz(ssb.get("starBaseSC"))
        else:
            z += numz(bb.get("starBaseSD")) + numz(ssb.get("starBaseSD"))
    else:
        key = str(meta.get("id", "")).replace("_direct", "").replace("lunar_", "")
        bt = bb.get("lunarBaseType") or {}
        st = ssb.get("lunarBaseType") or {}
        z = numz(bb.get("lunarBase")) + numz(ssb.get("lunarBase")) + numz(bt.get(key)) + numz(st.get(key))
    return 1 + z / 100


# ------------------------------------------------------------------ 状态求值

def evaluate_state_at(state: Dict[str, Any], en: List[Dict[str, Any]],
                      at_time: Optional[float] = None) -> Dict[str, Any]:
    ct: Dict[str, int] = {}
    for c in en:
        ct[c.get("element")] = ct.get(c.get("element"), 0) + 1

    reso = {c["id"]: {"atkPct": 0.0, "hpPct": 0.0, "emFlat": 0.0, "defPct": 0.0, "dmgAll": 0.0}
            for c in state.get("chars", [])}
    if ct.get("pyro", 0) >= 2:
        for c in en:
            reso[c["id"]]["atkPct"] += 25
    if ct.get("hydro", 0) >= 2:
        for c in en:
            reso[c["id"]]["hpPct"] += 25
    if ct.get("dendro", 0) >= 2:
        for c in en:
            reso[c["id"]]["emFlat"] += 50
    if ct.get("geo", 0) >= 2:
        for c in en:
            reso[c["id"]]["dmgAll"] += 15

    buf = {c["id"]: _make_char_buff() for c in state.get("chars", [])}
    source_buf: Dict[str, Any] = {}
    for c in state.get("chars", []):
        for d in c.get("dmgSrcs") or []:
            source_buf[d.get("id")] = make_source_buff()

    res_shred = def_eb()
    def_shred = 0.0
    feather_effs: List[Dict[str, Any]] = []

    for owner in en:
        for t in active_talents(state, owner, at_time):
            for ef in t.get("effs") or []:
                v = numz(ef.get("value"))
                cat = ef.get("cat")
                etype = ef.get("type")
                if cat == "feather":
                    feather_effs.append({"attr": etype, "source": ef.get("featherSource") or "all",
                                         "percent": v, "ownerId": owner.get("id")})
                    continue
                tgts = _char_targets(ef, owner, en)
                stgts = _source_targets(ef, owner, en, source_buf)

                if etype in ("source_dmg_bonus", "source_final_mult"):
                    for sb in stgts:
                        if etype == "source_dmg_bonus":
                            sb["sourceDmgBonus"] += v
                        else:
                            sb["finalMults"].append(v / 100)
                    continue
                if etype == "star_sc_stacks":
                    for sb in stgts:
                        sb["starStacks"] = numz(sb.get("starStacks")) + v
                    continue
                if cat == "resShred":
                    ek = str(etype).replace("res_", "")
                    res_shred[ek] = numz(res_shred.get(ek)) + v
                    continue
                if cat == "defense":
                    if etype == "def_shred":
                        def_shred += v
                    elif etype == "def_ignore":
                        if stgts:
                            for sb in stgts:
                                sb["defIgnore"] += v
                        else:
                            for tc in tgts:
                                b = buf.get(tc["id"])
                                if b:
                                    b["defIgnore"] += v
                    continue

                target = ef.get("target") or "self"
                if target.startswith("source:") and stgts and cat in ("dmgType", "dmgElem", "reaction", "lunar", "star"):
                    for sb in stgts:
                        if not sb:
                            continue
                        if cat == "dmgType":
                            if etype == "NA":
                                sb["dNA"] += v
                            elif etype == "CA":
                                sb["dCA"] += v
                            elif etype == "PA":
                                sb["dPA"] += v
                            elif etype == "E":
                                sb["dE"] += v
                            elif etype == "Q":
                                sb["dQ"] += v
                            elif etype == "all":
                                sb["dAll"] += v
                        elif cat == "dmgElem":
                            ek = str(etype).replace("elem_", "")
                            sb["dElem"][ek] = numz(sb["dElem"].get(ek)) + v
                        elif cat == "reaction":
                            if etype == "amp_bonus":
                                sb["ampBonus"] += v
                            elif str(etype).startswith("trans_"):
                                tk = str(etype).replace("trans_", "")
                                sb["transBonus"][tk] = numz(sb["transBonus"].get(tk)) + v
                        elif cat == "lunar":
                            if etype == "spec_all":
                                sb["lunarAll"] += v
                            elif etype == "spec_direct":
                                sb["lunarDirect"] += v
                            elif etype == "spec_reaction":
                                sb["lunarReaction"] += v
                            elif etype == "spec_ascend":
                                sb["specAscend"] = numz(sb.get("specAscend")) + v
                            elif etype == "lunar_charged":
                                sb["lunarType"]["charged"] += v
                            elif etype == "lunar_bloom":
                                sb["lunarType"]["bloom"] += v
                            elif etype == "lunar_crystal":
                                sb["lunarType"]["crystal"] += v
                            elif etype == "lunar_base":
                                sb["lunarBase"] += v
                            elif etype == "lunar_base_charged":
                                sb["lunarBaseType"]["charged"] += v
                            elif etype == "lunar_base_bloom":
                                sb["lunarBaseType"]["bloom"] += v
                            elif etype == "lunar_base_crystal":
                                sb["lunarBaseType"]["crystal"] += v
                        elif cat == "star":
                            if etype == "star_all":
                                sb["starAll"] += v
                            elif etype == "star_sc_bonus":
                                sb["starBonus"] += v
                            elif etype == "star_sd_bonus":
                                sb["starSdBonus"] = numz(sb.get("starSdBonus")) + v
                            elif etype == "star_ascend":
                                sb["starAscends"].append(v / 100)
                            elif etype == "star_base":
                                sb["starBase"] += v
                            elif etype == "star_base_sc":
                                sb["starBaseSC"] += v
                            elif etype == "star_base_sd":
                                sb["starBaseSD"] += v
                    continue

                for tc in tgts:
                    b = buf.get(tc["id"])
                    if not b:
                        continue
                    if cat == "stat":
                        mapping = {
                            "base_atk": "baseAtk", "base_def": "baseDef", "base_hp": "baseHP",
                            "atk_flat": "atkFlat", "atk_pct": "atkPct", "def_flat": "defFlat",
                            "def_pct": "defPct", "hp_flat": "hpFlat", "hp_pct": "hpPct",
                            "em_flat": "emFlat", "critRate": "critRate", "critDMG": "critDMG",
                        }
                        key = mapping.get(etype)
                        if key:
                            b[key] += v
                    elif cat == "dmgType":
                        if etype == "NA":
                            b["dNA"] += v
                        elif etype == "CA":
                            b["dCA"] += v
                        elif etype == "PA":
                            b["dPA"] += v
                        elif etype == "E":
                            b["dE"] += v
                        elif etype == "Q":
                            b["dQ"] += v
                        elif etype == "all":
                            b["dAll"] += v
                    elif cat == "dmgElem":
                        ek = str(etype).replace("elem_", "")
                        b["dElem"][ek] = numz(b["dElem"].get(ek)) + v
                    elif cat == "reaction":
                        if etype == "amp_bonus":
                            b["ampBonus"] += v
                        elif str(etype).startswith("trans_"):
                            tk = str(etype).replace("trans_", "")
                            b["transBonus"][tk] = numz(b["transBonus"].get(tk)) + v
                    elif cat == "lunar":
                        if etype == "spec_all":
                            b["specAll"] += v
                        elif etype == "spec_direct":
                            b["specDirect"] += v
                        elif etype == "spec_reaction":
                            b["specReaction"] += v
                        elif etype == "spec_ascend":
                            b["specAscend"] = numz(b.get("specAscend")) + v
                        elif etype == "lunar_charged":
                            b["lunarType"]["charged"] += v
                        elif etype == "lunar_bloom":
                            b["lunarType"]["bloom"] += v
                        elif etype == "lunar_crystal":
                            b["lunarType"]["crystal"] += v
                        elif etype == "lunar_base":
                            b["lunarBase"] += v
                        elif etype == "lunar_base_charged":
                            b["lunarBaseType"]["charged"] += v
                        elif etype == "lunar_base_bloom":
                            b["lunarBaseType"]["bloom"] += v
                        elif etype == "lunar_base_crystal":
                            b["lunarBaseType"]["crystal"] += v
                    elif cat == "star":
                        if etype == "star_all":
                            b["starAll"] += v
                        elif etype == "star_sc_bonus":
                            b["starBonus"] += v
                        elif etype == "star_sd_bonus":
                            b["starSdBonus"] = numz(b.get("starSdBonus")) + v
                        elif etype == "star_ascend":
                            b["starAscends"].append(v / 100)
                        elif etype == "star_base":
                            b["starBase"] += v
                        elif etype == "star_base_sc":
                            b["starBaseSC"] += v
                        elif etype == "star_base_sd":
                            b["starBaseSD"] += v

    fs: Dict[str, Dict[str, float]] = {}
    for c in state.get("chars", []):
        b = buf.get(c["id"]) or _make_char_buff()
        r = reso.get(c["id"]) or {"atkPct": 0, "hpPct": 0, "emFlat": 0, "defPct": 0, "dmgAll": 0}
        b_atk = numz(c.get("baseAtk")) + numz(c.get("weaponAtk")) + numz(b.get("baseAtk"))
        atk = b_atk * (1 + (numz(c.get("atkPct")) + b["atkPct"] + r["atkPct"]) / 100) + (numz(c.get("atkFlat")) + b["atkFlat"])
        dfn = (numz(c.get("baseDef")) + numz(b.get("baseDef"))) * (1 + (numz(c.get("defPct")) + b["defPct"] + r["defPct"]) / 100) + (numz(c.get("defFlat")) + b["defFlat"])
        hp = (numz(c.get("baseHP")) + numz(b.get("baseHP"))) * (1 + (numz(c.get("hpPct")) + b["hpPct"] + r["hpPct"]) / 100) + (numz(c.get("hpFlat")) + b["hpFlat"])
        em = numz(c.get("em")) + b["emFlat"] + r["emFlat"]
        fs[c["id"]] = {"atk": atk, "def": dfn, "hp": hp, "em": em,
                       "cr": numz(c.get("critRate")) + b["critRate"],
                       "cd": numz(c.get("critDMG")) + b["critDMG"]}

    return {"en": en, "fs": fs, "buf": buf, "sourceBuf": source_buf, "resShred": res_shred,
            "defShred": def_shred, "featherEffs": feather_effs, "reso": reso, "atTime": at_time}


# ------------------------------------------------------------------ 单次结算

def compute_single_hit(state: Dict[str, Any], d: Dict[str, Any], owner: Dict[str, Any],
                       st: Dict[str, Any], override_fs: Optional[Dict[str, Any]] = None,
                       mult_scale: float = 1.0, feather_scale: float = 1.0) -> Optional[Dict[str, Any]]:
    en = st["en"]
    fs = st["fs"]
    buf = st["buf"]
    source_buf = st["sourceBuf"]
    res_shred = st["resShred"]
    def_shred = st["defShred"]
    feather_effs = st["featherEffs"]
    reso = st["reso"]
    at_time = st["atTime"]
    enemy_res = state["enemy"]["res"]
    enemy_level = numz(state["enemy"].get("level"))

    trigger_id = d.get("triggerCharId") or owner.get("id")
    c = next((x for x in en if x.get("id") == trigger_id), None) or owner
    f = (override_fs or {}).get(c["id"]) or fs.get(c["id"]) or dict(_DEFAULT_FS)
    b = buf.get(c["id"]) or make_source_buff()
    r = reso.get(c["id"]) or {"atkPct": 0, "hpPct": 0, "emFlat": 0, "defPct": 0, "dmgAll": 0}
    sb = source_buf.get(d.get("id")) or make_source_buff()

    stat_owner_id = d.get("statCharId") or d.get("triggerCharId") or owner.get("id")
    stat_owner = next((x for x in en if x.get("id") == stat_owner_id), None) or c
    sf = (override_fs or {}).get(stat_owner["id"]) or fs.get(stat_owner["id"]) or f

    def calc_res(elem: str) -> float:
        base = enemy_res.get(elem)
        base = 10.0 if base is None else numz(base)
        e_res = base - numz((res_shred or {}).get(elem)) - numz((sb.get("resShred") or {}).get(elem))
        if e_res < 0:
            return 1 - e_res / 200
        if e_res <= 75:
            return 1 - e_res / 100
        return 1 / (4 * e_res / 100 + 1)

    def crit_zone() -> float:
        return 1 + (max(0.0, min(100.0, f["cr"])) / 100) * (f["cd"] / 100)

    def ascend_mult() -> float:
        """v2.1.7：擢升之间为加算。"""
        total = 0.0
        for o in en:
            for t in active_talents(state, o, at_time):
                for ef in t.get("effs") or []:
                    if ef.get("cat") in ("lunar", "star") and ef.get("type") == "spec_ascend":
                        tgt = ef.get("target") or ""
                        if tgt == "team" or o.get("id") == c.get("id") or tgt.startswith("source:"):
                            total += numz(ef.get("value")) / 100
        return 1 + total

    feather_add = 0.0
    feather_by_owner: Dict[str, float] = {}
    for fl in feather_effs:
        if fl["source"] != "all" and fl["source"] != "source:" + str(d.get("id")):
            continue
        if fl["attr"] == "fixed":
            fl_val = fl["percent"]
        else:
            owner_panel = (override_fs or {}).get(fl["ownerId"]) or fs.get(fl["ownerId"]) or sf
            fl_val = numz(owner_panel.get(fl["attr"])) * fl["percent"] / 100
        fl_val *= feather_scale
        feather_add += fl_val
        feather_by_owner[fl["ownerId"]] = feather_by_owner.get(fl["ownerId"], 0.0) + fl_val

    dtype = d.get("type")

    # ---------------------------------------------------------- 特殊直伤
    if dtype == "special_direct":
        meta = get_spec_meta(d.get("specType"))
        if not meta or not d.get("stat"):
            return None
        is_star = bool(meta.get("star"))
        dmg_elem = meta["elem"]
        if d.get("specType") in ("star_sc_direct", "star_sd_direct"):
            dmg_elem = c.get("element") or dmg_elem
        stat_map = {"atk": sf["atk"], "def": sf["def"], "hp": sf["hp"], "em": sf["em"]}
        stat_val = numz(d.get("fixedBase")) if d.get("stat") == "fixed" else numz(stat_map.get(d.get("stat")))
        base = stat_val * (numz(d.get("mult")) / 100) * mult_scale
        em_bonus = 6 * f["em"] / (f["em"] + 2000)
        key = str(meta["id"]).replace("_direct", "")
        spec_bonus = b.get("specBonus") or {}
        lunar_bonus = (numz(b.get("specAll")) / 100 + numz(b.get("lunarAll")) / 100
                       + numz(b.get("specDirect")) / 100 + numz(spec_bonus.get(meta["id"])) / 100
                       + numz(spec_bonus.get(key)) / 100)
        star_bonus = (numz(b.get("starAll")) / 100 + numz(b.get("starBonus")) / 100
                      + numz(b.get("starSdBonus")) / 100 + numz(sb.get("starSdBonus")) / 100)
        bonus = (star_bonus if is_star else lunar_bonus) + numz(sb.get("sourceDmgBonus")) / 100
        base_zone = base_zone_for(b, sb, meta)
        res_m = calc_res(dmg_elem)
        sfm = 1.0
        for m in sb.get("finalMults") or []:
            sfm *= m
        lunar_asc = ascend_mult()
        star_asc = 1 + sum(list(b.get("starAscends") or []) + list(sb.get("starAscends") or []))
        asc = star_asc if is_star else lunar_asc
        mult = meta.get("mult") or 1
        if meta.get("star"):
            if d.get("specType") == "star_sc_direct":
                mult = get_star_base_mult(d, numz(sb.get("starStacks")))
            elif d.get("specType") == "star_sd_direct":
                mult = 1.0
        main_nc = base * mult * base_zone * (1 + em_bonus + bonus) * res_m * asc * sfm
        feather_nc = feather_add * base_zone * res_m * asc
        non_crit = main_nc + feather_nc
        crit = main_nc * (1 + f["cd"] / 100) + feather_nc * (1 + f["cd"] / 100)
        main_expected = base * mult * base_zone * (1 + em_bonus + bonus) * crit_zone() * res_m * asc * sfm
        feather_multiplier = base_zone * res_m * asc * crit_zone()
        expected = main_expected + feather_add * feather_multiplier
        shares = {c["id"]: main_expected}
        detail_shares = {"direct": {c["id"]: main_expected}, "feather": {}, "reaction": 0.0}
        if feather_add > 0:
            for oid, fv in feather_by_owner.items():
                fdmg = fv * feather_multiplier
                shares[oid] = shares.get(oid, 0.0) + fdmg
                detail_shares["feather"][oid] = detail_shares["feather"].get(oid, 0.0) + fdmg
        return {"charId": c["id"], "charName": c.get("name"), "dName": d.get("name"), "elem": dmg_elem,
                "expected": expected, "crit": jround(crit), "nonCrit": jround(non_crit),
                "isSpecDirect": True, "ownerName": owner.get("name"), "shares": shares,
                "detailShares": detail_shares}

    # ---------------------------------------------------------- 特殊反应
    if dtype == "special_reaction":
        meta = get_spec_meta(d.get("specType"))
        if not meta:
            return None
        is_star = bool(meta.get("star"))
        res_m = calc_res(meta["elem"])
        sfm = 1.0
        for m in sb.get("finalMults") or []:
            sfm *= m
        mult = meta.get("mult") or 1
        if meta.get("star"):
            if meta.get("cryoChoice"):
                mult = 3 if numz(d.get("starSwirlCryoMult")) == 3 else 2
            elif meta["id"] == "star_sd_anemo":
                mult = 0.75

        def calc_component(cc: Dict[str, Any]) -> Dict[str, float]:
            cf = (override_fs or {}).get(cc["id"]) or fs.get(cc["id"]) or dict(_DEFAULT_FS)
            cb = buf.get(cc["id"]) or {}
            em_bonus_c = 6 * cf["em"] / (cf["em"] + 2000)
            lunar_bonus_c = (numz(cb.get("specAll")) / 100 + numz(cb.get("lunarAll")) / 100
                             + numz(cb.get("specReaction")) / 100 + numz(sb.get("sourceDmgBonus")) / 100)
            star_bonus_c = (numz(cb.get("starAll")) / 100 + numz(cb.get("starBonus")) / 100
                            + numz(cb.get("starSdBonus")) / 100 + numz(sb.get("starSdBonus")) / 100)
            bonus_c = star_bonus_c if is_star else lunar_bonus_c
            base_zone_c = base_zone_for(cb, sb, meta)
            s_c = 0.0
            for o in en:
                for t in active_talents(state, o, at_time):
                    for ef in t.get("effs") or []:
                        if ef.get("cat") in ("lunar", "star") and ef.get("type") == "spec_ascend":
                            tgt = ef.get("target") or ""
                            if tgt == "team" or o.get("id") == cc.get("id") or tgt.startswith("source:"):
                                s_c += numz(ef.get("value")) / 100
            lunar_asc_c = 1 + s_c
            star_asc_c = 1 + sum(list(cb.get("starAscends") or []) + list(sb.get("starAscends") or []))
            asc_c = star_asc_c if is_star else lunar_asc_c
            cr_cl_c = max(0.0, min(100.0, cf["cr"])) / 100
            crit_zone_c = 1 + cr_cl_c * (cf["cd"] / 100)
            base_c = (level_coeff(cc.get("lv")) * mult * base_zone_c * (1 + em_bonus_c + bonus_c)
                      * res_m * asc_c * sfm * mult_scale)
            return {"nonCrit": base_c, "crit": base_c * (1 + cf["cd"] / 100), "expected": base_c * crit_zone_c}

        contribs = [x for x in ((next((y for y in en if y.get("id") == cid), None)) for cid in (d.get("contribs") or [])) if x]
        if not contribs:
            if d.get("triggerCharId"):
                contribs = [c]
            else:
                return None

        tc = 1.0 if d.get("triggerCount") is None else max(0.0, numz(d.get("triggerCount")))
        comps = []
        for cc in contribs:
            comp = calc_component(cc)
            comp["element"] = cc.get("element")
            comps.append(comp)

        slots: List[Tuple[Dict[str, float], float]] = []
        if meta["id"] == "star_sd_anemo":
            anemos = sorted([x for x in comps if x["element"] == "anemo"], key=lambda x: -x["nonCrit"])
            top = anemos[0] if anemos else None
            if anemos:
                slots.append((anemos[0], 3 / 5))
            rest = sorted([x for x in comps if x is not top], key=lambda x: -x["nonCrit"])
            weights = [3 / 10, 1 / 20, 1 / 20]
            for i, x in enumerate(rest):
                slots.append((x, weights[i] if i < len(weights) else 0))
        elif meta["id"] == "star_sd_cryo":
            cryos = sorted([x for x in comps if x["element"] == "cryo"], key=lambda x: -x["nonCrit"])
            anemos = sorted([x for x in comps if x["element"] == "anemo"], key=lambda x: -x["nonCrit"])
            if cryos:
                slots.append((cryos[0], 3 / 5))
            if anemos:
                slots.append((anemos[0], 3 / 10))
            used = {id(s[0]) for s in slots}
            rest = sorted([x for x in comps if id(x) not in used], key=lambda x: -x["nonCrit"])
            weights = [1 / 20, 1 / 20]
            for i, x in enumerate(rest):
                slots.append((x, weights[i] if i < len(weights) else 0))
        else:
            weights = [1, 1 / 2, 1 / 12, 1 / 12]
            for i, x in enumerate(sorted(comps, key=lambda x: -x["nonCrit"])):
                slots.append((x, weights[i] if i < len(weights) else 0))

        non_crit = crit = single = 0.0
        for comp, w in slots:
            non_crit += comp["nonCrit"] * w
            crit += comp["crit"] * w
            single += comp["expected"] * w

        f_cr_cl = max(0.0, min(100.0, f["cr"])) / 100
        f_crit_zone = 1 + f_cr_cl * (f["cd"] / 100)
        if is_star:
            f_asc = 1 + sum(list(b.get("starAscends") or []) + list(sb.get("starAscends") or []))
        else:
            f_asc = ascend_mult()
        base_zone_f = base_zone_for(b, sb, meta)
        reaction_expected = single * tc
        feather_multiplier = base_zone_f * res_m * f_asc * f_crit_zone * tc
        total_expected = reaction_expected + feather_add * feather_multiplier
        shares = {"__reaction__": reaction_expected}
        detail_shares = {"direct": {}, "feather": {}, "reaction": reaction_expected}
        if feather_add > 0:
            for oid, fv in feather_by_owner.items():
                fdmg = fv * feather_multiplier
                shares[oid] = shares.get(oid, 0.0) + fdmg
                detail_shares["feather"][oid] = detail_shares["feather"].get(oid, 0.0) + fdmg
        final_non_crit = (non_crit + feather_add * base_zone_f * res_m * f_asc) * tc
        final_crit = (crit + feather_add * base_zone_f * res_m * f_asc * (1 + f["cd"] / 100)) * tc
        return {"charId": c["id"], "charName": c.get("name"), "dName": d.get("name"), "elem": meta["elem"],
                "expected": total_expected, "crit": jround(final_crit), "nonCrit": jround(final_non_crit),
                "isSpecReaction": True, "ownerName": owner.get("name"), "shares": shares,
                "detailShares": detail_shares}

    # ---------------------------------------------------------- 剧变反应
    if dtype == "trans":
        tr = TRANS_BY_ID.get(d.get("transType"))
        if not tr:
            return None
        tc = 1.0 if d.get("triggerCount") is None else max(0.0, numz(d.get("triggerCount")))
        lv_c = level_coeff(c.get("lv"))
        em = f["em"]
        source_final = 1.0
        for m in sb.get("finalMults") or []:
            source_final *= m
        elem_for_res = tr["elem"]
        base_res = enemy_res.get(elem_for_res)
        base_res = 10.0 if base_res is None else numz(base_res)
        e_res = base_res - numz(res_shred.get(elem_for_res)) - numz(sb["resShred"].get(elem_for_res))
        if e_res < 0:
            res_mult = 1 - e_res / 200
        elif e_res <= 75:
            res_mult = 1 - e_res / 100
        else:
            res_mult = 1 / (4 * e_res / 100 + 1)

        if tr.get("quicken"):
            quicken_bonus = numz(b["transBonus"].get(tr["id"])) / 100 + numz(sb["transBonus"].get(tr["id"])) / 100
            base_dmg = lv_c * tr["mult"] * (1 + 5 * em / (em + 1200) + quicken_bonus) * mult_scale
            db_pct = (numz(c.get("allDmgBonus")) + numz(r.get("dmgAll")) + numz(b.get("dAll"))
                      + numz(sb.get("dAll")) + numz(sb.get("sourceDmgBonus")))
            db_pct += (numz((c.get("elemDmgBonus") or {}).get(tr["elem"]))
                       + numz((b.get("dElem") or {}).get(tr["elem"]))
                       + numz((sb.get("dElem") or {}).get(tr["elem"])))
            db_mult = 1 + db_pct / 100
            cd_v = f["cd"] / 100
            crit_exp = 1 + max(0.0, min(100.0, f["cr"])) / 100 * cd_v
            d_sm = max(0.0, 1 - (def_shred + numz(sb.get("defShred"))) / 100)
            d_im = max(0.0, 1 - (numz(b.get("defIgnore")) + numz(sb.get("defIgnore"))) / 100)
            lv = numz(c.get("lv"))
            def_m = (lv + 100) / ((lv + 100) + (enemy_level + 100) * d_sm * d_im)
            non_crit = base_dmg * db_mult * def_m * res_mult * source_final
            crit = non_crit * (1 + cd_v)
            single = base_dmg * db_mult * crit_exp * def_m * res_mult * source_final
            exp = single * tc
            return {"charId": c["id"], "charName": c.get("name"), "dName": d.get("name"), "elem": tr["elem"],
                    "expected": exp, "crit": jround(crit * tc), "nonCrit": jround(non_crit * tc),
                    "isTrans": True, "isQuicken": True, "ownerName": owner.get("name"),
                    "shares": {"__reaction__": exp},
                    "detailShares": {"direct": {}, "feather": {}, "reaction": exp}}

        em_bonus = 16 * em / (em + 2000)
        base_tk = "swirl" if str(tr["id"]).startswith("swirl") else tr["id"]
        trans_bonus_pct = (numz(b["transBonus"].get(base_tk)) / 100 + numz(sb["transBonus"].get(base_tk)) / 100
                           + numz(sb.get("sourceDmgBonus")) / 100)
        base_dmg = lv_c * tr["mult"] * (1 + em_bonus + trans_bonus_pct) * mult_scale
        feather_multiplier = (1 + em_bonus + trans_bonus_pct) * res_mult * tc * source_final
        base_reaction_dmg = base_dmg * res_mult * tc * source_final
        total_expected = base_reaction_dmg + feather_add * feather_multiplier
        shares = {"__reaction__": base_reaction_dmg}
        detail_shares = {"direct": {}, "feather": {}, "reaction": base_reaction_dmg}
        if feather_add > 0:
            for oid, fv in feather_by_owner.items():
                fdmg = fv * feather_multiplier
                shares[oid] = shares.get(oid, 0.0) + fdmg
                detail_shares["feather"][oid] = detail_shares["feather"].get(oid, 0.0) + fdmg
        return {"charId": c["id"], "charName": c.get("name"), "dName": d.get("name"), "elem": tr["elem"],
                "expected": total_expected, "crit": None, "nonCrit": jround(total_expected),
                "isTrans": True, "ownerName": owner.get("name"), "shares": shares,
                "detailShares": detail_shares}

    # ---------------------------------------------------------- 普通伤害
    if not d.get("stat") or not d.get("element"):
        return None
    stat_map = {"atk": sf["atk"], "def": sf["def"], "hp": sf["hp"], "em": sf["em"]}
    sv = numz(d.get("fixedBase")) if d.get("stat") == "fixed" else numz(stat_map.get(d.get("stat")))
    base_with_add = sv * (numz(d.get("mult")) / 100) * mult_scale + feather_add
    db_pct = (numz(c.get("allDmgBonus")) + numz(r.get("dmgAll")) + numz(b.get("dAll"))
              + numz(sb.get("dAll")) + numz(sb.get("sourceDmgBonus")))
    elem = d.get("element")
    db_pct += (numz((c.get("elemDmgBonus") or {}).get(elem)) + numz((b.get("dElem") or {}).get(elem))
               + numz((sb.get("dElem") or {}).get(elem)))
    dt = d.get("dmgType")
    if dt == "NA":
        db_pct += numz(b.get("dNA")) + numz(sb.get("dNA"))
    elif dt == "CA":
        db_pct += numz(b.get("dCA")) + numz(sb.get("dCA"))
    elif dt == "PA":
        db_pct += numz(b.get("dPA")) + numz(sb.get("dPA"))
    elif dt == "E":
        db_pct += numz(b.get("dE")) + numz(sb.get("dE"))
    elif dt == "Q":
        db_pct += numz(b.get("dQ")) + numz(sb.get("dQ"))
    db_mult = 1 + db_pct / 100
    cd_v = f["cd"] / 100
    crit_exp = 1 + max(0.0, min(100.0, f["cr"])) / 100 * cd_v
    d_sm = max(0.0, 1 - (def_shred + numz(sb.get("defShred"))) / 100)
    d_im = max(0.0, 1 - (numz(b.get("defIgnore")) + numz(sb.get("defIgnore"))) / 100)
    lv = numz(c.get("lv"))
    def_m = (lv + 100) / ((lv + 100) + (enemy_level + 100) * d_sm * d_im)
    base_res2 = enemy_res.get(elem)
    base_res2 = 10.0 if base_res2 is None else numz(base_res2)
    e_res2 = base_res2 - numz((res_shred or {}).get(elem)) - numz((sb.get("resShred") or {}).get(elem))
    if e_res2 < 0:
        res_m2 = 1 - e_res2 / 200
    elif e_res2 <= 75:
        res_m2 = 1 - e_res2 / 100
    else:
        res_m2 = 1 / (4 * e_res2 / 100 + 1)
    amp_m = 1.0
    if d.get("reaction") in ("vape", "melt"):
        em_b = 2.78 * f["em"] / (f["em"] + 1400)
        if d.get("reaction") == "vape":
            b_a = 2 if elem == "hydro" else 1.5
        else:
            b_a = 2 if elem == "pyro" else 1.5
        amp_m = b_a * (1 + em_b + numz(b.get("ampBonus")) / 100 + numz(sb.get("ampBonus")) / 100)
    source_final = 1.0
    for m in sb.get("finalMults") or []:
        source_final *= m
    mult_common = db_mult * def_m * res_m2 * amp_m * source_final
    char_base = sv * (numz(d.get("mult")) / 100) * mult_scale
    char_expected = char_base * mult_common * crit_exp
    total_expected = base_with_add * mult_common * crit_exp
    non_crit = base_with_add * mult_common
    crit = base_with_add * mult_common * (1 + cd_v)
    shares = {c["id"]: char_expected}
    detail_shares = {"direct": {c["id"]: char_expected}, "feather": {}, "reaction": 0.0}
    if feather_add > 0:
        for oid, fv in feather_by_owner.items():
            fdmg = fv * mult_common * crit_exp
            shares[oid] = shares.get(oid, 0.0) + fdmg
            detail_shares["feather"][oid] = detail_shares["feather"].get(oid, 0.0) + fdmg
    return {"charId": c["id"], "charName": c.get("name"), "dName": d.get("name"), "elem": elem,
            "expected": total_expected, "crit": jround(crit), "nonCrit": jround(non_crit),
            "isTrans": False, "ownerName": owner.get("name"), "shares": shares,
            "detailShares": detail_shares}


# ------------------------------------------------------------------ 主结算

SLICE_COUNT = 20


def calc(state: Dict[str, Any]) -> Dict[str, Any]:
    """对应 HTML 的 calc()，返回与 window.__lastCalc 同构的结果。"""
    en = [c for c in state.get("chars", []) if c.get("on")]
    rot = max(1.0, num(state.get("rotationDuration"), 20))
    static_state = evaluate_state_at(state, en, None)
    results: List[Dict[str, Any]] = []
    inspect_map: Dict[str, Any] = {}

    if not state.get("timelineEnabled"):
        for owner in en:
            for d in owner.get("dmgSrcs") or []:
                if not d.get("on") or not dmg_source_valid(d):
                    continue
                hit = compute_single_hit(state, d, owner, static_state, None, 1.0, 1.0)
                if hit:
                    row = dict(hit)
                    row.update({"sourceId": d.get("id"), "timingMode": "instant",
                                "startTime": 0, "duration": 0})
                    results.append(row)
                    inspect_map[d.get("id")] = {"d": d, "owner": owner, "startState": static_state,
                                                "expected": hit["expected"], "crit": hit["crit"],
                                                "nonCrit": hit["nonCrit"]}
    else:
        cache: Dict[float, Dict[str, Any]] = {}

        def state_at(t: float) -> Dict[str, Any]:
            key = round(t, 9)
            got = cache.get(key)
            if got is None:
                got = evaluate_state_at(state, en, t)
                cache[key] = got
            return got

        for owner in en:
            for d in owner.get("dmgSrcs") or []:
                if not d.get("on") or not dmg_source_valid(d):
                    continue
                mode = d.get("timingMode") or "instant"
                t_start = ((numz(d.get("startTime")) % rot) + rot) % rot
                dur = max(0.0, numz(d.get("duration")))
                start_state = state_at(t_start)
                snapshot_fs = start_state["fs"] if mode == "uniform_snapshot" else None

                src_expected = 0.0
                last_crit = 0.0
                last_non_crit = 0.0
                meta_res: Optional[Dict[str, Any]] = None
                src_shares: Dict[str, float] = {}
                src_detail = {"direct": {}, "feather": {}, "reaction": 0.0}

                if mode == "instant" or dur == 0:
                    hit = compute_single_hit(state, d, owner, start_state, None, 1.0, 1.0)
                    if hit:
                        meta_res = hit
                        src_expected = hit["expected"]
                        last_crit = hit["crit"] or 0
                        last_non_crit = hit["nonCrit"] or 0
                        src_shares = dict(hit.get("shares") or {})
                        src_detail = hit.get("detailShares") or src_detail
                        inspect_map[d.get("id")] = {"d": d, "owner": owner, "startState": start_state,
                                                    "expected": src_expected, "crit": last_crit,
                                                    "nonCrit": last_non_crit}
                else:
                    n = SLICE_COUNT
                    dt = dur / n
                    weight = 1.0 / n
                    for i in range(n):
                        sample_time = (((t_start + (i + 0.5) * dt) % rot) + rot) % rot
                        cur_state = state_at(sample_time)
                        slice_hit = compute_single_hit(state, d, owner, cur_state, snapshot_fs, weight, weight)
                        if slice_hit:
                            meta_res = slice_hit
                            src_expected += slice_hit["expected"]
                            last_crit += slice_hit["crit"] or 0
                            last_non_crit += slice_hit["nonCrit"] or 0
                            for k, v in (slice_hit.get("shares") or {}).items():
                                src_shares[k] = src_shares.get(k, 0.0) + v
                            ds = slice_hit.get("detailShares") or {}
                            for k, v in (ds.get("direct") or {}).items():
                                src_detail["direct"][k] = src_detail["direct"].get(k, 0.0) + v
                            for k, v in (ds.get("feather") or {}).items():
                                src_detail["feather"][k] = src_detail["feather"].get(k, 0.0) + v
                            src_detail["reaction"] += ds.get("reaction") or 0.0
                    if meta_res:
                        inspect_map[d.get("id")] = {"d": d, "owner": owner, "startState": start_state,
                                                    "expected": src_expected, "crit": last_crit,
                                                    "nonCrit": last_non_crit}

                if meta_res:
                    row = dict(meta_res)
                    row.update({"sourceId": d.get("id"), "expected": src_expected,
                                "crit": last_crit, "nonCrit": last_non_crit,
                                "timingMode": mode, "startTime": t_start, "duration": dur,
                                "shares": src_shares, "detailShares": src_detail})
                    results.append(row)

    total = sum(r.get("expected") or 0.0 for r in results)
    dps = (total / rot) if state.get("timelineEnabled") else 0.0
    total_shares: Dict[str, float] = {}
    total_detail = {"direct": {}, "feather": {}, "reaction": 0.0}
    for r in results:
        for k, v in (r.get("shares") or {}).items():
            total_shares[k] = total_shares.get(k, 0.0) + v
        ds = r.get("detailShares") or {}
        for k, v in (ds.get("direct") or {}).items():
            total_detail["direct"][k] = total_detail["direct"].get(k, 0.0) + v
        for k, v in (ds.get("feather") or {}).items():
            total_detail["feather"][k] = total_detail["feather"].get(k, 0.0) + v
        total_detail["reaction"] += ds.get("reaction") or 0.0

    panels = []
    for c in state.get("chars", []):
        f = static_state["fs"].get(c["id"]) or {}
        panels.append({"id": c["id"], "name": c.get("name"), "level": c.get("lv"),
                       "element": c.get("element"), "enabled": bool(c.get("on")),
                       "atk": f.get("atk", 0.0), "def": f.get("def", 0.0), "hp": f.get("hp", 0.0),
                       "em": f.get("em", 0.0), "cr": f.get("cr", 0.0), "cd": f.get("cd", 0.0)})

    return {"fs": static_state["fs"], "buf": static_state["buf"], "reso": static_state["reso"],
            "en": en, "results": results, "total": total, "dps": dps, "inspectMap": inspect_map,
            "sourceBuf": static_state["sourceBuf"], "shares": total_shares,
            "detailShares": total_detail, "panels": panels}


# ------------------------------------------------------------------ 技能面板分段

def get_skill_panel_intervals(state: Dict[str, Any], d: Dict[str, Any], owner: Dict[str, Any],
                              en: List[Dict[str, Any]], rot: float) -> List[Dict[str, Any]]:
    """对应 HTML 的 getSkillPanelIntervals()。"""
    t_start = ((numz(d.get("startTime")) % rot) + rot) % rot
    dur = max(0.0, numz(d.get("duration")))
    mode = d.get("timingMode") or "instant"
    trigger_id = d.get("triggerCharId") or owner.get("id")
    c = next((x for x in en if x.get("id") == trigger_id), None) or owner

    if mode == "instant" or dur == 0:
        st = evaluate_state_at(state, en, t_start)
        return [{"start": t_start, "end": t_start, "duration": 0,
                 "fs": st["fs"].get(c["id"]) or dict(_DEFAULT_FS),
                 "talents": active_talents(state, owner, t_start), "isSnapshot": False}]

    if mode == "uniform_snapshot":
        st = evaluate_state_at(state, en, t_start)
        return [{"start": t_start, "end": t_start + dur, "duration": dur,
                 "fs": st["fs"].get(c["id"]) or dict(_DEFAULT_FS),
                 "talents": active_talents(state, owner, t_start), "isSnapshot": True}]

    t_end = t_start + dur
    break_points = {t_start, t_end}
    for o in en:
        manual = [t for t in (o.get("talents") or [])
                  if t.get("on") and (not t.get("source") or t.get("source") == "manual") and talent_valid(t)]
        all_t = manual + [t for t in equipment_talents(o) if talent_valid(t)]
        for t in all_t:
            if t.get("isPermanent"):
                continue
            t_dur = max(0.0, numz(t.get("duration")))
            t_st = ((numz(t.get("startTime")) % rot) + rot) % rot
            k = -1
            while k <= math.ceil(t_end / rot) + 1:
                st_shift = t_st + k * rot
                end_shift = st_shift + t_dur
                if t_start < st_shift < t_end:
                    break_points.add(st_shift)
                if t_start < end_shift < t_end:
                    break_points.add(end_shift)
                k += 1

    pts = sorted(break_points)
    raw: List[Dict[str, Any]] = []
    for i in range(len(pts) - 1):
        seg_start, seg_end = pts[i], pts[i + 1]
        seg_dur = seg_end - seg_start
        if seg_dur <= 0.001:
            continue
        mid = (((seg_start + seg_dur * 0.5) % rot) + rot) % rot
        st = evaluate_state_at(state, en, mid)
        raw.append({"start": seg_start, "end": seg_end, "duration": seg_dur,
                    "fs": st["fs"].get(c["id"]) or dict(_DEFAULT_FS),
                    "talents": active_talents(state, owner, mid), "isSnapshot": False})

    merged: List[Dict[str, Any]] = []
    for inv in raw:
        if not merged:
            merged.append(inv)
            continue
        prev = merged[-1]
        same_stats = (jround(prev["fs"]["atk"]) == jround(inv["fs"]["atk"])
                      and jround(prev["fs"]["def"]) == jround(inv["fs"]["def"])
                      and jround(prev["fs"]["hp"]) == jround(inv["fs"]["hp"])
                      and jround(prev["fs"]["em"]) == jround(inv["fs"]["em"])
                      and jround(prev["fs"]["cr"] * 10) == jround(inv["fs"]["cr"] * 10)
                      and jround(prev["fs"]["cd"] * 10) == jround(inv["fs"]["cd"] * 10))
        same_talents = (len(prev["talents"]) == len(inv["talents"])
                        and all(t.get("name") == (inv["talents"][i].get("name") if i < len(inv["talents"]) else None)
                                for i, t in enumerate(prev["talents"])))
        if same_stats and same_talents:
            prev["end"] = inv["end"]
            prev["duration"] += inv["duration"]
        else:
            merged.append(inv)
    return merged
