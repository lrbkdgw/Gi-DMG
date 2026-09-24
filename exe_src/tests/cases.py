"""对拍用的随机配置生成器（固定随机种子，保证可复现）。"""

from __future__ import annotations

import random
from typing import Any, Dict, List

EL_IDS = ["pyro", "hydro", "electro", "cryo", "dendro", "anemo", "geo", "physical"]
DT_IDS = ["NA", "CA", "PA", "E", "Q", "other"]
TRANS_IDS = ["aggravate", "spread", "overloaded", "superconduct", "electrocharged",
             "swirl_pyro", "swirl_hydro", "swirl_electro", "swirl_cryo", "shattered",
             "bloom", "hyperbloom", "burgeon", "burning"]
SPEC_DIRECT = ["lunar_bloom_direct", "lunar_charged_direct", "lunar_crystal_direct",
               "star_sc_direct", "star_sd_direct"]
SPEC_REACTION = ["lunar_charged", "lunar_crystal", "star_sd_cryo", "star_sd_anemo"]
STATS = ["atk", "def", "hp", "em", "fixed"]
TIMING = ["instant", "uniform_snapshot", "uniform_dynamic"]

EFF_POOL = [
    ("stat", ["base_atk", "base_def", "base_hp", "atk_flat", "atk_pct", "def_flat", "def_pct",
              "hp_flat", "hp_pct", "em_flat", "critRate", "critDMG"]),
    ("dmgType", ["NA", "CA", "PA", "E", "Q", "all", "source_dmg_bonus", "source_final_mult"]),
    ("dmgElem", ["elem_" + e for e in EL_IDS]),
    ("resShred", ["res_" + e for e in EL_IDS]),
    ("defense", ["def_shred", "def_ignore"]),
    ("reaction", ["amp_bonus", "trans_aggravate", "trans_spread", "trans_overloaded",
                  "trans_superconduct", "trans_electrocharged", "trans_swirl", "trans_shattered",
                  "trans_bloom", "trans_hyperbloom", "trans_burgeon", "trans_burning"]),
    ("lunar", ["spec_all", "spec_direct", "spec_reaction", "lunar_charged", "lunar_bloom",
               "lunar_crystal", "lunar_base", "lunar_base_charged", "lunar_base_bloom",
               "lunar_base_crystal", "spec_ascend"]),
    ("star", ["star_all", "star_sc_bonus", "star_sc_stacks", "star_sd_bonus", "star_base",
              "star_base_sc", "star_base_sd", "star_ascend"]),
    ("feather", ["atk", "def", "hp", "em", "fixed"]),
]


def _mk_source(rnd: random.Random, idx: int, char_ids: List[str], own_id: str) -> Dict[str, Any]:
    kind = rnd.choice(["normal", "normal", "trans", "special_direct", "special_reaction"])
    sid = f"s{idx}"
    base: Dict[str, Any] = {
        "id": sid, "on": rnd.random() > 0.12, "type": kind, "name": f"来源{idx}",
        "timingMode": rnd.choice(TIMING),
        "startTime": round(rnd.uniform(0, 25), 1),
        "duration": round(rnd.uniform(0, 18), 1),
        "triggerCharId": rnd.choice(char_ids + [own_id, ""]),
        "statCharId": rnd.choice(char_ids + [own_id, ""]),
    }
    if kind == "normal":
        base.update({
            "stat": rnd.choice(STATS), "mult": round(rnd.uniform(20, 900), 1),
            "element": rnd.choice(EL_IDS), "dmgType": rnd.choice(DT_IDS),
            "reaction": rnd.choice(["none", "vape", "melt"]),
            "fixedBase": round(rnd.uniform(100, 5000), 1),
        })
    elif kind == "trans":
        base.update({"transType": rnd.choice(TRANS_IDS), "triggerCount": rnd.randint(1, 6)})
    elif kind == "special_direct":
        base.update({
            "specType": rnd.choice(SPEC_DIRECT), "stat": rnd.choice(STATS),
            "mult": round(rnd.uniform(50, 600), 1), "starStacks": rnd.randint(0, 12),
            "fixedBase": round(rnd.uniform(100, 3000), 1),
        })
    else:
        picks = [cid for cid in char_ids if rnd.random() > 0.45]
        base.update({
            "specType": rnd.choice(SPEC_REACTION), "triggerCount": rnd.randint(1, 4),
            "contribs": picks, "starSwirlCryoMult": rnd.choice([2, 3]),
        })
    return base


def _mk_effect(rnd: random.Random, char_ids: List[str], source_ids: List[str]) -> Dict[str, Any]:
    cat, types = rnd.choice(EFF_POOL)
    ef: Dict[str, Any] = {"cat": cat, "type": rnd.choice(types),
                          "value": round(rnd.uniform(-30, 120), 1)}
    if cat == "feather":
        ef["featherSource"] = rnd.choice(["all"] + ["source:" + s for s in source_ids])
    else:
        targets = ["self", "team"] + ["char:" + c for c in char_ids] + ["source:" + s for s in source_ids]
        ef["target"] = rnd.choice(targets)
    return ef


def build_cases(seed: int = 20250924, count: int = 60) -> List[Dict[str, Any]]:
    rnd = random.Random(seed)
    cases: List[Dict[str, Any]] = []
    for ci in range(count):
        n_chars = rnd.randint(1, 4)
        char_ids = [f"c{ci}_{i}" for i in range(n_chars)]
        chars: List[Dict[str, Any]] = []
        source_ids: List[str] = []
        src_counter = 0
        for i, cid in enumerate(char_ids):
            n_src = rnd.randint(0, 3)
            srcs = []
            for _ in range(n_src):
                src_counter += 1
                s = _mk_source(rnd, src_counter, char_ids, cid)
                srcs.append(s)
                source_ids.append(s["id"])
            chars.append({
                "id": cid, "on": rnd.random() > 0.1, "name": f"角色{ci}-{i}",
                "lv": rnd.choice([1, 40, 60, 80, 90, 93, 100]),
                "element": rnd.choice(EL_IDS),
                "baseAtk": round(rnd.uniform(80, 400), 1), "weaponAtk": round(rnd.uniform(300, 750), 1),
                "atkPct": round(rnd.uniform(0, 120), 1), "atkFlat": round(rnd.uniform(0, 500), 1),
                "baseDef": round(rnd.uniform(400, 900), 1), "defPct": round(rnd.uniform(0, 80), 1),
                "defFlat": round(rnd.uniform(0, 200), 1),
                "baseHP": round(rnd.uniform(9000, 18000), 1), "hpPct": round(rnd.uniform(0, 120), 1),
                "hpFlat": round(rnd.uniform(0, 6000), 1),
                "em": round(rnd.uniform(0, 1000), 1), "critRate": round(rnd.uniform(5, 105), 1),
                "critDMG": round(rnd.uniform(50, 260), 1), "allDmgBonus": round(rnd.uniform(0, 40), 1),
                "elemDmgBonus": {e: round(rnd.uniform(0, 70), 1) if rnd.random() > 0.6 else 0 for e in EL_IDS},
                "dmgSrcs": srcs, "talents": [],
            })
        # 角色天赋（需要在所有来源 id 都已知之后再生成，才能指向任意来源）
        for c in chars:
            for ti in range(rnd.randint(0, 3)):
                c["talents"].append({
                    "id": f"{c['id']}_t{ti}", "on": rnd.random() > 0.15, "source": "manual",
                    "name": f"天赋{ti}", "startTime": round(rnd.uniform(0, 22), 1),
                    "duration": round(rnd.uniform(0, 30), 1), "isPermanent": False,
                    "effs": [_mk_effect(rnd, char_ids, source_ids) for _ in range(rnd.randint(1, 3))],
                })
            # 武器 / 圣遗物天赋
            w_talents = []
            for wi in range(rnd.randint(0, 2)):
                w_talents.append({
                    "id": f"{c['id']}_w{wi}", "on": rnd.random() > 0.2, "name": f"武器天赋{wi}",
                    "startTime": round(rnd.uniform(0, 20), 1),
                    "duration": rnd.choice([None, 0, 5.5, 12, 20, 40]),
                    "effs": [_mk_effect(rnd, char_ids, source_ids) for _ in range(rnd.randint(1, 2))],
                })
            a_sets = []
            for ai in range(rnd.randint(0, 2)):
                a_sets.append({
                    "name": f"套装{ai}", "on": rnd.random() > 0.2,
                    "startTime": round(rnd.uniform(0, 20), 1),
                    "duration": rnd.choice([None, 4, 15, 20, 25]),
                    "effs": [_mk_effect(rnd, char_ids, source_ids) for _ in range(rnd.randint(1, 2))],
                })
            c["qs"] = {
                "base": {"hp": 0, "atk": 0, "def": 0, "ascType": "none", "ascPhase": 6, "ascVal": 0},
                "weapon": {"level": 90, "rarity": 5, "atkTier": "542", "atk": 0, "subType": "none",
                           "subVal": 0, "name": "武器", "talents": w_talents},
                "artifact": {"subs": {}, "mains": {"sand": "none", "goblet": "none", "circlet": "none"},
                             "sets": a_sets},
            }
        cases.append({
            "timelineEnabled": rnd.random() > 0.3,
            "dmgShareEnabled": True,
            "rotationDuration": rnd.choice([8, 12, 20, 20, 31.5]),
            "enemy": {"level": rnd.choice([1, 60, 93, 100, 120]),
                      "res": {e: rnd.choice([-20, 0, 10, 10, 40, 75, 90]) for e in EL_IDS}},
            "chars": chars,
            "selId": char_ids[0],
            "baselines": [],
            "baselineMode": "a",
        })
    return cases
