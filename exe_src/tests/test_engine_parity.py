"""Python 引擎 ↔ HTML(JS) 引擎 对拍测试。

运行： cd exe_src && python -m pytest tests -q
需要本机存在 node（CI 已内置）。没有 node 时自动跳过。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidmg.core import engine, state as st  # noqa: E402
from tests import js_reference  # noqa: E402
from tests.cases import build_cases  # noqa: E402

REL_TOL = 1e-9
ABS_TOL = 1e-6


def close(a, b, label=""):
    if a is None and b is None:
        return
    a = float(a or 0)
    b = float(b or 0)
    diff = abs(a - b)
    scale = max(1.0, abs(a), abs(b))
    assert diff <= max(ABS_TOL, REL_TOL * scale), f"{label}: python={a!r} js={b!r} diff={diff}"


@pytest.fixture(scope="module")
def cases():
    return build_cases()


@pytest.fixture(scope="module")
def js_results(cases):
    if not js_reference.node_available():
        pytest.skip("未安装 node，跳过对拍测试")
    return js_reference.JsEngine().run(cases)


def test_parity(cases, js_results):
    assert len(js_results) == len(cases)
    checked_sources = 0
    for idx, (case, expected) in enumerate(zip(cases, js_results)):
        s = st.normalize_state(case)
        got = engine.calc(s)
        close(got["total"], expected["total"], f"case{idx}.total")
        close(got["dps"], expected["dps"], f"case{idx}.dps")

        assert len(got["panels"]) == len(expected["panels"]), f"case{idx}: 面板数量不一致"
        for p, q in zip(got["panels"], expected["panels"]):
            assert p["id"] == q["id"]
            for k in ("atk", "def", "hp", "em", "cr", "cd"):
                close(p[k], q[k], f"case{idx}.panel[{p['id']}].{k}")

        assert len(got["results"]) == len(expected["results"]), (
            f"case{idx}: 伤害来源条目数不一致 "
            f"python={[r['sourceId'] for r in got['results']]} js={[r['sourceId'] for r in expected['results']]}"
        )
        for r, e in zip(got["results"], expected["results"]):
            tag = f"case{idx}.src[{e['sourceId']}]"
            assert r["sourceId"] == e["sourceId"], tag
            assert r["charId"] == e["charId"], tag + ".charId"
            assert r["elem"] == e["elem"], tag + ".elem"
            assert bool(r.get("isTrans")) == e["isTrans"], tag + ".isTrans"
            assert bool(r.get("isQuicken")) == e["isQuicken"], tag + ".isQuicken"
            assert bool(r.get("isSpecDirect")) == e["isSpecDirect"], tag + ".isSpecDirect"
            assert bool(r.get("isSpecReaction")) == e["isSpecReaction"], tag + ".isSpecReaction"
            assert r["timingMode"] == e["timingMode"], tag + ".timingMode"
            close(r["startTime"], e["startTime"], tag + ".startTime")
            close(r["duration"], e["duration"], tag + ".duration")
            close(r["expected"], e["expected"], tag + ".expected")
            close(r["crit"], e["crit"], tag + ".crit")
            close(r["nonCrit"], e["nonCrit"], tag + ".nonCrit")
            assert set(r["shares"].keys()) == set(e["shares"].keys()), tag + ".shares.keys"
            for k in r["shares"]:
                close(r["shares"][k], e["shares"][k], f"{tag}.shares[{k}]")
            checked_sources += 1

        assert set(got["shares"].keys()) == set(expected["shares"].keys()), f"case{idx}.shares.keys"
        for k in got["shares"]:
            close(got["shares"][k], expected["shares"][k], f"case{idx}.shares[{k}]")
        for bucket in ("direct", "feather"):
            assert set(got["detailShares"][bucket].keys()) == set(expected["detailShares"][bucket].keys()), \
                f"case{idx}.detailShares.{bucket}.keys"
            for k in got["detailShares"][bucket]:
                close(got["detailShares"][bucket][k], expected["detailShares"][bucket][k],
                      f"case{idx}.detailShares.{bucket}[{k}]")
        close(got["detailShares"]["reaction"], expected["detailShares"]["reaction"],
              f"case{idx}.detailShares.reaction")

    assert checked_sources > 140, f"覆盖的伤害来源过少（{checked_sources}）"


def test_level_coeff_matches_table():
    assert engine.level_coeff(90) == pytest.approx(1446.85)
    assert engine.level_coeff(1) == pytest.approx(17.17)
    # 线性插值
    assert engine.level_coeff(92) == pytest.approx(1446.85 + (1711.20 - 1446.85) * (2 / 5))


def test_star_coefficients():
    assert engine.star_coeff_from_stacks(0) == pytest.approx(1.00)
    assert engine.star_coeff_from_stacks(1) == pytest.approx(1.45)
    assert engine.star_coeff_from_stacks(12) == pytest.approx(1.45 + 0.05 * 11)
