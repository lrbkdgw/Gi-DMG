#!/usr/bin/env python3
"""把提交 2e43850 中的原版 HTML 按区块拆到 /tmp/gi-orig（只读参考与构建输入）。"""
import pathlib, subprocess
REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path('/tmp/gi-orig'); OUT.mkdir(exist_ok=True)
raw = subprocess.run(['git', '-C', str(REPO), 'show', '2e43850:Gi DMG v2.2.0.html'], capture_output=True, check=True).stdout.decode('utf8')
lines = raw.split('\n')
PARTS = [('01_head.html', 1, 7), ('02_tailwind.css', 8, 8), ('03_fontlinks.html', 9, 11), ('04_lucide.js', 12, 24),
         ('05_legacy.css', 25, 84), ('06_studio.css', 85, 1148), ('07_katex.css', 1149, 1150), ('08_katex.js', 1151, 1151),
         ('09_body.html', 1152, 1533), ('10_main.js', 1534, 4540), ('11_tail.html', 4541, 4544)]
for name, a, b in PARTS:
    (OUT / name).write_text('\n'.join(lines[a - 1:b]) + '\n', encoding='utf8')
(OUT / 'full.html').write_text(raw, encoding='utf8')
print('split ok:', len(lines), 'lines')
