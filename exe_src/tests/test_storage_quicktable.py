"""date/ 目录持久化与快速拉表的单元测试。"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidmg.core import quicktable as qt, state as st  # noqa: E402
from gidmg.core.storage import Storage  # noqa: E402


def demo_state(*keys: str):
    """用内置预设角色拼一个可用的配置。"""
    s = st.def_state()
    s["chars"] = [st.build_preset(k) for k in (keys or ("hutao", "yelan"))]
    s["selId"] = s["chars"][0]["id"]
    return st.normalize_state(s)


@pytest.fixture()
def store(tmp_path):
    s = Storage(tmp_path / "date")
    s.ensure()
    return s


def test_directory_layout(store, tmp_path):
    assert (tmp_path / "date" / "configs").is_dir()
    assert (tmp_path / "date" / "library").is_dir()
    assert (tmp_path / "date" / "history").is_dir()


def test_config_round_trip(store):
    s = demo_state()
    name = store.create_config("蒸发队", s)
    assert store.config_exists(name)
    back = store.load_config(name)
    assert [c["name"] for c in back["chars"]] == [c["name"] for c in s["chars"]]
    assert back["rotationDuration"] == s["rotationDuration"]

    metas = store.list_configs()
    assert len(metas) == 1 and metas[0].name == name
    assert metas[0].char_names == [c["name"] for c in s["chars"]]


def test_duplicate_names_get_suffix(store):
    s = st.def_state()
    a = store.create_config("配置", s)
    b = store.create_config("配置", s)
    c = store.create_config("配置", s)
    assert [a, b, c] == ["配置", "配置 2", "配置 3"]


def test_unsafe_names_are_sanitised(store):
    name = store.create_config('a/b\\c:d*?"<>|', st.def_state())
    assert "/" not in name and "\\" not in name
    assert store.load_config(name) is not None


def test_rename_and_duplicate_and_delete(store):
    s = st.def_state()
    store.create_config("原名", s)
    new = store.rename_config("原名", "新名")
    assert new == "新名" and not store.config_exists("原名")
    dup = store.duplicate_config("新名")
    assert dup == "新名 副本" and store.config_exists(dup)
    store.delete_config(dup)
    assert not store.config_exists(dup)


def test_import_export_is_html_compatible(store, tmp_path):
    """导出的 JSON 不带 EXE 外壳，HTML 版可以直接导入。"""
    s = demo_state("nahida", "raiden")
    store.create_config("融化队", s)
    out = tmp_path / "out.json"
    store.export_config("融化队", out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert "chars" in raw and "format" not in raw

    again = store.import_config(out, "回来的配置")
    assert [c["name"] for c in store.load_config(again)["chars"]] == [c["name"] for c in s["chars"]]


def test_import_accepts_exe_wrapped_file(store, tmp_path):
    store.create_config("A", st.def_state())
    wrapped = store.config_path("A")
    name = store.import_config(wrapped, "B")
    assert store.config_exists(name)


def test_draft_lifecycle(store):
    s = demo_state()
    store.create_config("草稿测试", s)
    assert store.load_draft("草稿测试") is None

    s["chars"][0]["name"] = "改过的名字"
    store.save_draft("草稿测试", s)
    assert store.list_configs()[0].has_draft
    assert store.load_draft("草稿测试")["chars"][0]["name"] == "改过的名字"
    # 正式保存会清掉草稿
    store.save_config("草稿测试", s)
    assert store.load_draft("草稿测试") is None


def test_libraries_and_settings(store):
    store.save_weapon_lib([{"name": "薄荷", "rarity": 5}])
    assert store.load_weapon_lib()[0]["name"] == "薄荷"
    store.save_artifact_lib([{"name": "追忆"}])
    assert store.load_artifact_lib()[0]["name"] == "追忆"

    assert store.load_settings()["cfgHistCount"] == 5
    store.update_settings(cfgHistCount=3, lastConfig="X")
    assert store.load_settings()["cfgHistCount"] == 3
    assert store.load_settings()["lastConfig"] == "X"


def test_history_is_trimmed_and_deduped(store):
    store.update_settings(cfgHistCount=3)
    s = st.normalize_state(st.def_state())
    for i in range(6):
        s["rotationDuration"] = 10 + i
        store.capture_cfg_history(s, 1000 + i, "配置")
    hist = store.load_cfg_history()
    assert len(hist) == 3
    assert hist[0]["total"] == 1005  # 最新的在最前

    # 内容一致时只刷新时间，不新增条目
    before = len(store.load_cfg_history())
    store.capture_cfg_history(s, 9999, "配置")
    after = store.load_cfg_history()
    assert len(after) == before and after[0]["total"] == 9999


def test_corrupt_files_do_not_crash(store):
    store.config_path("坏文件").write_text("{ 这不是 json", encoding="utf-8")
    store.settings_path.write_text("nope", encoding="utf-8")
    store.weapons_path.write_text("[[[", encoding="utf-8")
    assert store.list_configs() == []
    assert store.load_settings()["cfgHistCount"] == 5
    assert store.load_weapon_lib() == []


# ----------------------------------------------------------------- 快速拉表

def _scheme(char_id, name, cost, snap, **over):
    s = copy.deepcopy(snap)
    s.update(over)
    return qt.Scheme(char_id=char_id, name=name, cost=cost, snapshot=s)


def test_quicktable_enumerates_cartesian_product():
    s = demo_state()
    ids = [c["id"] for c in s["chars"] if c["on"]]
    assert len(ids) >= 2
    schemes = {
        ids[0]: [_scheme(ids[0], "低配", 0, s["chars"][0], critDMG=100),
                 _scheme(ids[0], "高配", 10, s["chars"][0], critDMG=250)],
        ids[1]: [_scheme(ids[1], "A", 0, s["chars"][1]),
                 _scheme(ids[1], "B", 5, s["chars"][1], atkPct=200),
                 _scheme(ids[1], "C", 8, s["chars"][1], em=800)],
    }
    seen = []
    rows = qt.run(s, schemes, progress=lambda d, t: seen.append((d, t)) is None)
    assert len(rows) == 6
    assert {r.cost for r in rows} == {0, 5, 8, 10, 15, 18}
    assert all(r.total > 0 for r in rows)
    assert seen and seen[-1][0] == 6 and seen[-1][1] == 6
    # 高暴伤方案必定不低于低暴伤方案
    by = {(r.schemes[ids[0]], r.schemes[ids[1]]): r.total for r in rows}
    assert by[("高配", "A")] >= by[("低配", "A")]


def test_quicktable_does_not_mutate_original_state():
    s = demo_state()
    before = json.dumps(s, sort_keys=True)
    qt.run(s, {})
    assert json.dumps(s, sort_keys=True) == before


def test_quicktable_cancel():
    s = demo_state()
    ids = [c["id"] for c in s["chars"] if c["on"]]
    schemes = {ids[0]: [_scheme(ids[0], f"方案{i}", i, s["chars"][0], critDMG=50 + 10 * i)
                        for i in range(40)]}
    rows = qt.run(s, schemes, progress=lambda d, t: False)
    assert 0 < len(rows) < 40


def test_prune_dominated():
    mk = lambda cost, total: qt.QtResult(cost, {}, total, total / 20, {})
    rows = [mk(0, 100), mk(5, 100), mk(5, 200), mk(10, 150), mk(10, 300)]
    kept = qt.prune_dominated(rows)
    kept_pairs = sorted((r.cost, r.total) for r in kept)
    # (5,100) 被 (0,100) 偏序；(10,150) 被 (5,200) 偏序
    assert kept_pairs == [(0, 100), (5, 200), (10, 300)]


def test_sorting_matches_html_rules():
    mk = lambda cost, dps: qt.QtResult(cost, {}, dps * 20, dps, {})
    rows = [mk(10, 500), mk(0, 300), mk(10, 900), mk(5, 900)]
    a = qt.sort_results(list(rows), "cost", cost_asc=True)
    assert [(r.cost, r.dps) for r in a] == [(0, 300), (5, 900), (10, 900), (10, 500)]
    b = qt.sort_results(list(rows), "dmg", dmg_asc=False)
    assert [(r.cost, r.dps) for r in b] == [(5, 900), (10, 900), (10, 500), (0, 300)]


def test_export_csv_and_markdown(tmp_path):
    rows = [qt.QtResult(3, {"a": "方案1", "b": "默认"}, 240000, 12000,
                        {"a": 180000, "b": 60000, "__reaction__": 40000})]
    info = [{"id": "a", "name": "角色甲"}, {"id": "b", "name": "角色乙"}]
    csv_text = qt.to_csv(rows, info, show_share=True, has_reaction=True)
    assert csv_text.startswith("\ufeff")
    header, row = csv_text.lstrip("\ufeff").strip().split("\n")
    assert header == "成本,角色甲,角色乙,DPS,角色甲 占比,角色乙 占比,反应 占比"
    assert row == "3,方案1,默认,12000,75.0%,25.0%,16.7%"

    md = qt.to_markdown(rows, info, show_share=False, has_reaction=False)
    assert md.splitlines()[0] == "| 成本 | 角色甲 | 角色乙 | DPS |"
    assert md.splitlines()[2] == "| 3 | 方案1 | 默认 | 12,000 |"

    p = tmp_path / "t.csv"
    qt.write_csv(p, rows, info, True, True)
    assert p.read_text(encoding="utf-8").startswith("\ufeff成本")
