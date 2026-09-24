"""把 HTML 版的结算引擎跑在 Node 上，作为 Python 引擎的对拍基准。

做法：从 `html_bin/Gi DMG v2.1.9.html` 中抽出主脚本，前置一套 DOM 打桩，后置
一个驱动程序，然后用 node 执行。任何 HTML 侧的公式改动都会立刻反映到对拍结果。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HTML = REPO_ROOT / "html_bin" / "Gi DMG v2.1.9.html"

STUBS = r"""
const mkDummy = () => new Proxy(function(){}, {
  get(t,k){
    if(k==='length') return 0;
    if(k===Symbol.iterator) return function*(){};
    if(k===Symbol.toPrimitive) return ()=>'';
    if(k==='toString') return ()=>'';
    if(k==='forEach'||k==='map'||k==='filter') return ()=>[];
    return dummy;
  },
  set(){return true;}, apply(){return dummy;}, construct(){return dummy;}, has(){return true;},
});
const dummy = mkDummy();
globalThis.document = {
  getElementById: ()=>dummy, querySelector: ()=>dummy, querySelectorAll: ()=>[],
  createElement: ()=>dummy, addEventListener: ()=>{}, body: dummy, documentElement: dummy,
};
globalThis.window = globalThis;
globalThis.addEventListener = ()=>{};
globalThis.requestAnimationFrame = ()=>{};
globalThis.MutationObserver = class { observe(){} disconnect(){} };
globalThis.localStorage = { _d:{}, getItem(k){return this._d[k]??null;},
  setItem(k,v){this._d[k]=String(v);}, removeItem(k){delete this._d[k];} };
globalThis.alert = ()=>{}; globalThis.confirm = ()=>true; globalThis.prompt = ()=>null;
globalThis.navigator = { clipboard: { writeText: async()=>{} } };
globalThis.Blob = class {}; globalThis.URL = { createObjectURL: ()=>'', revokeObjectURL: ()=>{} };
globalThis.FileReader = class {};
globalThis.katex = null; globalThis.lucide = null;
globalThis.HTMLSelectElement = class {};
"""

DRIVER = r"""
const fs = require('fs');
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
suppressCalcUI = true;
const out = [];
for (const cs of cases) {
  S = normalizeState(JSON.parse(JSON.stringify(cs)));
  calc();
  const lc = window.__lastCalc;
  out.push({
    total: lc.total, dps: lc.dps,
    panels: lc.panels.map(p=>({id:p.id, atk:p.atk, def:p.def, hp:p.hp, em:p.em, cr:p.cr, cd:p.cd})),
    results: lc.results.map(r=>({
      sourceId: r.sourceId, charId: r.charId, dName: r.dName, elem: r.elem,
      expected: r.expected, crit: r.crit, nonCrit: r.nonCrit,
      isTrans: !!r.isTrans, isQuicken: !!r.isQuicken,
      isSpecDirect: !!r.isSpecDirect, isSpecReaction: !!r.isSpecReaction,
      timingMode: r.timingMode, startTime: r.startTime, duration: r.duration,
      shares: r.shares,
    })),
    shares: lc.shares, detailShares: lc.detailShares,
  });
}
process.stdout.write(JSON.stringify(out));
"""


def extract_app_script(html_path: Path) -> str:
    """取出 HTML 中体积最大的内联脚本（即计算器主脚本）。"""
    text = html_path.read_text(encoding="utf-8")
    best = ""
    for m in re.finditer(r"<script([^>]*)>", text):
        attrs = m.group(1)
        if "src=" in attrs or "lucide" in attrs or "katex" in attrs:
            continue
        end = text.find("</script>", m.end())
        if end < 0:
            continue
        body = text[m.end():end]
        if len(body) > len(best):
            best = body
    if not best:
        raise RuntimeError("未能在 HTML 中找到主脚本")
    return best


def node_available() -> bool:
    return shutil.which("node") is not None


class JsEngine:
    """把若干配置一次性丢给 node 计算，返回结构化结果。"""

    def __init__(self, html_path: Optional[Path] = None) -> None:
        self.html_path = Path(html_path or DEFAULT_HTML)
        self._dir = Path(tempfile.mkdtemp(prefix="gidmg-jsref-"))
        script = STUBS + "\n" + extract_app_script(self.html_path) + "\n" + DRIVER
        self._script = self._dir / "engine_ref.js"
        self._script.write_text(script, encoding="utf-8")

    def run(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = self._dir / "cases.json"
        payload.write_text(json.dumps(cases), encoding="utf-8")
        proc = subprocess.run(
            ["node", str(self._script), str(payload)],
            capture_output=True, text=True, timeout=600,
            env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=1024"},
        )
        if proc.returncode != 0:
            raise RuntimeError(f"node 执行失败：{proc.stderr[-4000:]}")
        return json.loads(proc.stdout)
