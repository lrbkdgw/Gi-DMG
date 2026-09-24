"""快捷配置助手（快速面板推算）与 HTML 版的对拍测试。

覆盖 inferWeapon / inferAscension / applyStatType / applyQS 四个环节，
比较应用后角色对象的全部面板字段与天赋列表。
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import subprocess
from typing import Any, Dict, List

import pytest

from gidmg.core import quickset as qsc, state as st
from gidmg.core.constants import EL

from . import js_reference as jsref

QS_DRIVER = r"""
const fs = require('fs');
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const cs of cases) {
  const ch = JSON.parse(JSON.stringify(cs));
  inferAscension(ch.qs);
  inferWeapon(ch.qs);
  applyQS(ch);
  out.push({
    atkFlat: ch.atkFlat, atkPct: ch.atkPct, hpFlat: ch.hpFlat, hpPct: ch.hpPct,
    defFlat: ch.defFlat, defPct: ch.defPct, em: ch.em, critRate: ch.critRate,
    critDMG: ch.critDMG, allDmgBonus: ch.allDmgBonus,
    elemDmgBonus: ch.elemDmgBonus,
    qsBase: ch.qs.base, qsWeapon: {atk: ch.qs.weapon.atk, subVal: ch.qs.weapon.subVal},
    talents: (ch.talents || []).map(t => ({
      name: t.name, source: t.source, on: t.on, isPermanent: t.isPermanent,
      duration: t.duration, startTime: t.startTime,
      effs: (t.effs || []).map(e => ({cat: e.cat, type: e.type, value: e.value, target: e.target})),
    })),
  });
}
process.stdout.write(JSON.stringify(out));
"""


class JsQuickSet:
    """在 node 上执行 HTML 版的快捷配置推算。"""

    def __init__(self) -> None:
        import tempfile
        from pathlib import Path
        self._dir = Path(tempfile.mkdtemp(prefix="gidmg-qsref-"))
        script = (jsref.STUBS + "\n" + jsref.extract_app_script(jsref.DEFAULT_HTML)
                  + "\n" + QS_DRIVER)
        self._script = self._dir / "quickset_ref.js"
        self._script.write_text(script, encoding="utf-8")

    def run(self, chars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = self._dir / "cases.json"
        payload.write_text(json.dumps(chars), encoding="utf-8")
        proc = subprocess.run(["node", str(self._script), str(payload)],
                              capture_output=True, text=True, timeout=300,
                              encoding="utf-8", errors="replace",  # 同上，避免 Windows 解码乱码
                              env={**os.environ})
        if proc.returncode != 0:
            raise RuntimeError(f"node 执行失败：{proc.stderr[-4000:]}")
        return json.loads(proc.stdout)


SUB_KEYS = ["atk_pct", "hp_pct", "def_pct", "em", "cr", "cd", "atk_flat", "hp_flat", "def_flat"]
ASC_TYPES = ["none", "atk_pct", "hp_pct", "def_pct", "em", "cr", "cd", "pyro_dmg", "hydro_dmg",
             "electro_dmg", "cryo_dmg", "dendro_dmg", "anemo_dmg", "geo_dmg", "physical_dmg",
             "heal_bonus", "er"]
WPN_SUBS = ["none", "atk_pct", "hp_pct", "def_pct", "em", "cr", "cd", "er", "physical_dmg"]
SAND = ["none", "atk_pct", "hp_pct", "def_pct", "em", "er"]
GOBLET = ["none", "atk_pct", "hp_pct", "def_pct", "em", "pyro_dmg", "hydro_dmg", "electro_dmg",
          "cryo_dmg", "dendro_dmg", "anemo_dmg", "geo_dmg", "physical_dmg"]
CIRCLET = ["none", "atk_pct", "hp_pct", "def_pct", "em", "cr", "cd", "heal_bonus"]


def _valid(options: List[str], known: List[str]) -> List[str]:
    """只对拍两边都支持的选项，避免 HTML 侧没有的 key 造成假阳性。"""
    return [o for o in options if o in known] or ["none"]


def build_quickset_cases(count: int = 48, seed: int = 20250924) -> List[Dict[str, Any]]:
    rnd = random.Random(seed)
    from gidmg.core.constants import ART_MAIN_VALUE, ART_SUB_VALUE, ASC_MAX

    asc_types = _valid(ASC_TYPES, list(ASC_MAX.keys()) + ["none"])
    main_keys = list(ART_MAIN_VALUE.keys())
    sub_keys = [k for k in SUB_KEYS if k in ART_SUB_VALUE]

    cases: List[Dict[str, Any]] = []
    for i in range(count):
        elem = rnd.choice([e["id"] for e in EL])
        ch = st.def_char(elem)
        ch["name"] = f"对拍角色{i}"
        ch["lv"] = rnd.choice([1, 40, 70, 80, 90, 100])
        # 预置一个手动天赋 + 一个应当被 applyQS 清掉的装备天赋
        manual = st.new_talent("手动天赋")
        manual["source"] = "manual"
        manual["effs"][0].update(cat="stat", type="atk_pct", value=20, target="self")
        stale = st.new_talent("旧武器天赋")
        stale["source"] = "weapon"
        stale["effs"][0].update(cat="stat", type="atk_pct", value=99, target="self")
        ch["talents"] = [manual, stale] if i % 3 else [stale]

        qs = st.def_qs()
        qs["base"].update(
            hp=rnd.choice([0, 10000, 12345.6]),
            atk=rnd.choice([0, 250, 311.7]),
            **{"def": rnd.choice([0, 600, 876.5])},
            ascType=rnd.choice(asc_types),
            ascPhase=rnd.randint(0, 6),
        )
        rarity = rnd.choice([3, 4, 5])
        tiers = qsc.weapon_tiers(rarity)
        qs["weapon"].update(
            level=rnd.choice([40, 50, 60, 70, 80, 90]),
            rarity=rarity,
            atkTier=str(rnd.choice(tiers)),
            subType=rnd.choice(_valid(WPN_SUBS, list(ART_MAIN_VALUE.keys()) + ["none", "er"])),
            name=f"武器{i}",
        )
        if i % 4 == 0:
            tal = {"id": st.uid(), "on": True, "name": f"武器天赋{i}", "startTime": 1,
                   "duration": 12, "effs": [dict(st.new_effect(),
                                                 cat="stat", type="atk_pct", value=18, target="self")]}
            qs["weapon"]["talents"] = [tal]

        qs["artifact"]["subs"] = {k: (rnd.choice([0, 1, 3, 6.5]) if k in sub_keys else 0)
                                  for k in SUB_KEYS}
        qs["artifact"]["mains"] = {
            "sand": rnd.choice(_valid(SAND, main_keys)),
            "goblet": rnd.choice(_valid(GOBLET, main_keys)),
            "circlet": rnd.choice(_valid(CIRCLET, main_keys)),
        }
        if i % 5 == 0:
            qs["artifact"]["sets"] = [{
                "name": f"套装{i}", "on": True, "startTime": 0, "duration": 20,
                "effs": [dict(st.new_effect(), cat="stat", type="critDMG", value=30, target="team")],
            }]
        ch["qs"] = qs
        cases.append(ch)
    return cases


def _close(a: Any, b: Any, tol: float = 1e-6) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=0, abs_tol=max(tol, abs(float(b)) * 1e-9))
    return a == b


@pytest.mark.skipif(not jsref.node_available(), reason="需要 node 才能运行对拍测试")
def test_quickset_matches_html() -> None:
    cases = build_quickset_cases()
    expected = JsQuickSet().run(copy.deepcopy(cases))
    assert len(expected) == len(cases)

    for idx, (case, exp) in enumerate(zip(cases, expected)):
        ch = copy.deepcopy(case)
        qsc.infer_ascension(ch["qs"])
        qsc.infer_weapon(ch["qs"])
        qsc.apply_quickset(ch)

        for key in ("atkFlat", "atkPct", "hpFlat", "hpPct", "defFlat", "defPct",
                    "em", "critRate", "critDMG", "allDmgBonus"):
            assert _close(ch.get(key, 0), exp[key]), f"[{idx}] {key}: {ch.get(key)} != {exp[key]}"

        for e in EL:
            got = (ch.get("elemDmgBonus") or {}).get(e["id"], 0)
            want = (exp["elemDmgBonus"] or {}).get(e["id"], 0)
            assert _close(got, want), f"[{idx}] elemDmgBonus.{e['id']}: {got} != {want}"

        assert _close(ch["qs"]["base"]["ascVal"], exp["qsBase"]["ascVal"]), f"[{idx}] ascVal"
        assert _close(ch["qs"]["weapon"]["atk"], exp["qsWeapon"]["atk"]), f"[{idx}] weapon.atk"
        assert _close(ch["qs"]["weapon"]["subVal"], exp["qsWeapon"]["subVal"]), f"[{idx}] weapon.subVal"

        got_tals = [{"name": t.get("name"), "source": t.get("source"), "on": t.get("on"),
                     "isPermanent": t.get("isPermanent"), "duration": t.get("duration"),
                     "startTime": t.get("startTime"),
                     "effs": [{"cat": e.get("cat"), "type": e.get("type"),
                               "value": e.get("value"), "target": e.get("target")}
                              for e in t.get("effs", [])]}
                    for t in ch.get("talents", [])]
        assert len(got_tals) == len(exp["talents"]), (
            f"[{idx}] 天赋数量 {len(got_tals)} != {len(exp['talents'])}")
        for gt, et in zip(got_tals, exp["talents"]):
            assert gt["name"] == et["name"], f"[{idx}] 天赋名 {gt['name']} != {et['name']}"
            assert gt["source"] == et["source"], f"[{idx}] 天赋来源 {gt['source']} != {et['source']}"
            assert len(gt["effs"]) == len(et["effs"]), f"[{idx}] 效果数量不一致"
            for ge, ee in zip(gt["effs"], et["effs"]):
                assert ge["cat"] == ee["cat"] and ge["type"] == ee["type"], f"[{idx}] 效果类型不一致"
                assert _close(ge["value"] or 0, ee["value"] or 0), f"[{idx}] 效果数值不一致"
                assert ge["target"] == ee["target"], f"[{idx}] 效果目标不一致"


@pytest.mark.skipif(not jsref.node_available(), reason="需要 node 才能运行对拍测试")
def test_quickset_case_coverage() -> None:
    """确保对拍样本确实覆盖了各类分支，避免测试空转。"""
    cases = build_quickset_cases()
    assert len(cases) >= 40
    assert len({c["qs"]["weapon"]["rarity"] for c in cases}) == 3
    assert len({c["qs"]["base"]["ascPhase"] for c in cases}) >= 5
    assert any(c["qs"]["weapon"].get("talents") for c in cases)
    assert any(c["qs"]["artifact"].get("sets") for c in cases)
    assert any(c["qs"]["artifact"]["mains"]["goblet"].endswith("_dmg") for c in cases)
