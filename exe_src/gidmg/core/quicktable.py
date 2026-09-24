"""快速拉表：角色方案笛卡尔积 → 批量结算 → 排序 / 偏序剔除 / 导出。

对应 HTML 的 runQuickTableAsync()、pruneDominated()、applyQuickTableSort()、
exportQuickTableCsv()。计算过程与 HTML 完全一致（同一套 calc()）。
"""

from __future__ import annotations

import copy
import csv
import io
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from . import engine
from .format import js_num, pct as fmt_pct, rounded
from .state import uid


@dataclass
class Scheme:
    """某个角色的一种配装方案（角色面板快照 + 代价）。"""
    char_id: str
    name: str
    cost: float = 0.0
    snapshot: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=uid)

    def to_json(self) -> Dict[str, Any]:
        return {"id": self.id, "charId": self.char_id, "name": self.name,
                "cost": self.cost, "snapshot": self.snapshot}

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "Scheme":
        return Scheme(char_id=str(d.get("charId", "")), name=str(d.get("name", "方案")),
                      cost=float(d.get("cost") or 0), snapshot=d.get("snapshot") or {},
                      id=str(d.get("id") or uid()))


@dataclass
class QtResult:
    cost: float
    schemes: Dict[str, str]
    total: float
    dps: float
    shares: Dict[str, float]

    def to_json(self) -> Dict[str, Any]:
        return {"cost": self.cost, "schemes": self.schemes, "total": self.total,
                "dps": self.dps, "shares": self.shares}

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "QtResult":
        return QtResult(cost=float(d.get("cost") or 0), schemes=dict(d.get("schemes") or {}),
                        total=float(d.get("total") or 0), dps=float(d.get("dps") or 0),
                        shares=dict(d.get("shares") or {}))


def build_options(state: Dict[str, Any],
                  schemes: Dict[str, List[Scheme]]) -> List[List[Scheme]]:
    """每个启用角色一组候选方案；没存方案的角色用其当前面板作为「默认」。"""
    out: List[List[Scheme]] = []
    for c in state.get("chars", []):
        if not c.get("on"):
            continue
        got = schemes.get(c["id"]) or []
        if got:
            out.append([Scheme(s.char_id, s.name, s.cost, copy.deepcopy(s.snapshot), s.id) for s in got])
        else:
            out.append([Scheme(c["id"], "默认", 0.0, copy.deepcopy(c))])
    return out


def count_combinations(options: Sequence[Sequence[Scheme]]) -> int:
    n = 1
    for group in options:
        n *= max(1, len(group))
    return n if options else 0


def run(state: Dict[str, Any],
        schemes: Dict[str, List[Scheme]],
        progress: Optional[Callable[[int, int], bool]] = None) -> List[QtResult]:
    """遍历所有组合并结算。

    progress(done, total) 每批调用一次，返回 False 表示请求取消。
    """
    options = build_options(state, schemes)
    total_combos = count_combinations(options)
    if not total_combos:
        return []

    base_chars = copy.deepcopy(state.get("chars", []))
    index_of = {c["id"]: i for i, c in enumerate(base_chars)}
    rot = max(1.0, float(state.get("rotationDuration") or 20))
    work = dict(state)
    results: List[QtResult] = []

    batch = max(10, min(50, -(-total_combos // 100)))
    for i, combo in enumerate(product(*options), start=1):
        chars = copy.deepcopy(base_chars)
        for c in chars:
            c["on"] = False
        for opt in combo:
            idx = index_of.get(opt.char_id)
            if idx is None:
                continue
            snap = copy.deepcopy(opt.snapshot)
            snap["on"] = True
            snap["id"] = opt.char_id
            chars[idx] = snap
        work["chars"] = chars
        out = engine.calc(work)
        results.append(QtResult(
            cost=sum(o.cost for o in combo),
            schemes={o.char_id: o.name for o in combo},
            total=out["total"],
            dps=out["total"] / rot,
            shares=dict(out["shares"]),
        ))
        if progress and (i % batch == 0 or i == total_combos):
            if progress(i, total_combos) is False:
                return results
    return results


def prune_dominated(rows: Sequence[QtResult]) -> List[QtResult]:
    """剔除被偏序方案：存在另一方案代价不高于它、总伤不低于它，且至少一项严格更优。"""
    keep: List[QtResult] = []
    for r in rows:
        dominated = any(
            o is not r and o.cost <= r.cost and o.total >= r.total
            and (o.cost < r.cost or o.total > r.total)
            for o in rows
        )
        if not dominated:
            keep.append(r)
    return keep


def sort_results(rows: List[QtResult], field_: str = "cost",
                 cost_asc: bool = True, dmg_asc: bool = False) -> List[QtResult]:
    """与 HTML applyQuickTableSort() 等价：主序之外用另一维做稳定次序。"""
    if field_ == "cost":
        rows.sort(key=lambda r: (r.cost if cost_asc else -r.cost, -r.dps))
    else:
        rows.sort(key=lambda r: (r.dps if dmg_asc else -r.dps, r.cost))
    return rows


def has_reaction_column(rows: Iterable[QtResult]) -> bool:
    return any((r.shares.get("__reaction__") or 0) > 0 for r in rows)


def _share_pct(r: QtResult, key: str) -> float:
    return (r.shares.get(key, 0.0) / r.total * 100) if r.total > 0 else 0.0


def build_table(rows: Sequence[QtResult], char_info: Sequence[Dict[str, str]],
                show_share: bool, has_reaction: bool,
                plain_numbers: bool = False) -> tuple[List[str], List[List[str]]]:
    names = [c["name"] for c in char_info]
    ids = [c["id"] for c in char_info]
    headers = ["成本", *names, "DPS"]
    if show_share:
        headers += [f"{n} 占比" for n in names]
        if has_reaction:
            headers.append("反应 占比")
    body: List[List[str]] = []
    for r in rows:
        dps_txt = js_num(engine.jround(r.dps)) if plain_numbers else rounded(r.dps)
        row = [js_num(r.cost), *[r.schemes.get(i, "-") for i in ids], dps_txt]
        if show_share:
            row += [fmt_pct(_share_pct(r, i)) for i in ids]
            if has_reaction:
                row.append(fmt_pct(_share_pct(r, "__reaction__")))
        body.append(row)
    return headers, body


def to_csv(rows: Sequence[QtResult], char_info: Sequence[Dict[str, str]],
           show_share: bool, has_reaction: bool) -> str:
    """UTF-8 BOM 的 CSV，Excel 直接双击可读（与 HTML 导出格式一致）。"""
    headers, body = build_table(rows, char_info, show_share, has_reaction,
                                plain_numbers=True)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(headers)
    for row in body:
        w.writerow(row)
    return "\ufeff" + buf.getvalue()


def to_markdown(rows: Sequence[QtResult], char_info: Sequence[Dict[str, str]],
                show_share: bool, has_reaction: bool) -> str:
    headers, body = build_table(rows, char_info, show_share, has_reaction)
    esc = lambda s: str(s).replace("|", "\\|")
    out = ["| " + " | ".join(esc(h) for h in headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in body]
    return "\n".join(out) + "\n"


def write_csv(path: Path, rows, char_info, show_share, has_reaction) -> None:
    Path(path).write_text(to_csv(rows, char_info, show_share, has_reaction), encoding="utf-8")


def write_markdown(path: Path, rows, char_info, show_share, has_reaction) -> None:
    Path(path).write_text(to_markdown(rows, char_info, show_share, has_reaction), encoding="utf-8")
