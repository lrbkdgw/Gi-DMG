#!/usr/bin/env python3
"""组装单文件应用：python3 redesign/build.py   （输出默认写回仓库根目录的 `Gi DMG v2.2.0.html`）

输入
  · 原版各区块（split.py 从提交 2e43850 拆出）：lucide / KaTeX / 主脚本 / 公式卡片，逐字复用或经 codemod 改写
  · src/body.html   新的静态结构
  · src/app.css     设计系统
  · Tailwind 3.4.17 按新内容重新生成（预设层与工具类分开内联，工具类排在 app.css 之后）
环境变量 GI_TARGET 可改输出路径。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
ORIG = pathlib.Path('/tmp/gi-orig')
GEN = pathlib.Path('/tmp/gi-gen'); GEN.mkdir(exist_ok=True)
TW = pathlib.Path('/tmp/tw')
TARGET = pathlib.Path(os.environ.get('GI_TARGET') or REPO / 'Gi DMG v2.2.0.html')


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f'[build] failed: {cmd}')
    return r.stdout


def read(p):
    return pathlib.Path(p).read_text(encoding='utf8')


# ---------------------------------------------------------------- 1. 原版区块 + 脚本改写
if not (ORIG / '10_main.js').exists():
    run([sys.executable, str(ROOT / 'split.py')])
print(run([sys.executable, str(ROOT / 'src' / 'codemod.py')]).strip())
main_js = read(GEN / 'main.js').rstrip('\n')
assert main_js.startswith('<script>') and main_js.endswith('</script>')

# ---------------------------------------------------------------- 2. 公式卡片（内容逐字沿用，只换外观类）
orig_body = read(ORIG / '09_body.html').split('\n')
cards = '\n'.join(orig_body[247:290])
assert cards.startswith('<div class="sc rounded-xl p-3.5">') and cards.rstrip().endswith('</div>'), 'formula block moved'
n_cards = cards.count('<div class="sc rounded-xl p-3.5"><div class="font-[700] text-[13.5px] mb-1.5 text-[#5a3f28]">')
assert n_cards == 8, n_cards
cards = cards.replace('<div class="sc rounded-xl p-3.5"><div class="font-[700] text-[13.5px] mb-1.5 text-[#5a3f28]">',
                      '<div class="formula-card"><div class="formula-title">')
for old, new in (('<div class="slider-unit mb-2">', '<div class="slider-unit">'),
                 ('<div class="mb-2">等级系数：<b class="text-[#2d2319]" id="fCoeff"></b></div>', '<div class="formula-coeff">等级系数：<b id="fCoeff"></b></div>'),
                 ('<div class="grid grid-cols-2 md:grid-cols-3 gap-1.5 text-[11.5px]" id="fReactGrid"></div>', '<div class="formula-react-grid" id="fReactGrid"></div>')):
    assert cards.count(old) == 1, old
    cards = cards.replace(old, new)
assert not re.search(r'-\[#|text-\[', cards), 'legacy class left in formula cards'

body = read(ROOT / 'src' / 'body.html')
assert body.count('<!--@FORMULA_CARDS@-->') == 1
body = body.replace('<!--@FORMULA_CARDS@-->', cards).rstrip('\n')

# ---------------------------------------------------------------- 3. Tailwind
(GEN / 'tw-content.html').write_text(body, encoding='utf8')
(GEN / 'tw-content.js').write_text('\n'.join(l for l in main_js.split('\n') if len(l) < 20000), encoding='utf8')
(GEN / 'tw-base.config.js').write_text('module.exports={content:[],corePlugins:{container:false}};', encoding='utf8')
(GEN / 'tw-util.config.js').write_text(
    'module.exports={content:[%s,%s],corePlugins:{preflight:false,container:false}};'
    % (json.dumps(str(GEN / 'tw-content.html')), json.dumps(str(GEN / 'tw-content.js'))), encoding='utf8')
(GEN / 'tw-base.in.css').write_text('@tailwind base;', encoding='utf8')
(GEN / 'tw-util.in.css').write_text('@tailwind utilities;', encoding='utf8')
cli = str(TW / 'node_modules' / '.bin' / 'tailwindcss')
run([cli, '-c', str(GEN / 'tw-base.config.js'), '-i', str(GEN / 'tw-base.in.css'), '-o', str(GEN / 'tw-base.css'), '--minify'], cwd=TW)
run([cli, '-c', str(GEN / 'tw-util.config.js'), '-i', str(GEN / 'tw-util.in.css'), '-o', str(GEN / 'tw-util.css'), '--minify'], cwd=TW)
tw_base = read(GEN / 'tw-base.css').strip()
tw_util = read(GEN / 'tw-util.css').strip()
app_css = read(ROOT / 'src' / 'app.css').rstrip('\n')
assert '</style' not in app_css and '</style' not in tw_base and '</style' not in tw_util

# ---------------------------------------------------------------- 4. 主题脚本
THEME_INIT = ("<script id=\"theme-init\">/* 首帧前确定主题：已保存的选择优先，否则跟随系统 */\n"
              "(function(){try{var t=localStorage.getItem('gs_theme');if(t!=='dark'&&t!=='light')"
              "t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';"
              "document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();\n</script>")
THEME_TOGGLE = ("<script id=\"theme-toggle\">/* 深色 / 浅色主题切换，选择保存在 localStorage.gs_theme */\n"
                "(function(){var btn=document.getElementById('btnTheme'),root=document.documentElement;if(!btn)return;\n"
                "function sync(){var dark=root.getAttribute('data-theme')==='dark',label=dark?'切换为浅色主题':'切换为深色主题';"
                "btn.setAttribute('aria-pressed',dark?'true':'false');btn.setAttribute('aria-label',label);btn.title=label;}\n"
                "btn.addEventListener('click',function(){var next=root.getAttribute('data-theme')==='dark'?'light':'dark';"
                "root.setAttribute('data-theme',next);try{localStorage.setItem('gs_theme',next);}catch(e){}sync();});\n"
                "sync();})();\n</script>")

# ---------------------------------------------------------------- 5. 组装
head = read(ORIG / '01_head.html').rstrip('\n')
assert head.endswith('</title>')
parts = [
    head,
    THEME_INIT,
    f'<style id="tw-base">{tw_base}</style>',
    read(ORIG / '04_lucide.js').rstrip('\n'),
    f'<style id="app-styles">\n{app_css}\n</style>',
    f'<style id="tw-utilities">{tw_util}</style>',
    read(ORIG / '07_katex.css').rstrip('\n'),
    read(ORIG / '08_katex.js').rstrip('\n'),
    body,
    main_js,
    THEME_TOGGLE,
    '</body>',
    '</html>',
]
html = '\n'.join(parts) + '\n'

# ---------------------------------------------------------------- 6. 自检
class Balance(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'path'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids = [], [], []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == 'id':
                self.ids.append(v)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        for k, v in attrs:
            if k == 'id':
                self.ids.append(v)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'unexpected </{tag}> (open: {self.stack[-3:]})')
        else:
            self.stack.pop()


chk = Balance()
chk.feed(body.split('<body>', 1)[1])
assert not chk.errors and not chk.stack, (chk.errors[:5], chk.stack[-5:])
orig_ids = set(re.findall(r'\bid="([^"]+)"', read(ORIG / '09_body.html')))
dups = sorted({i for i in chk.ids if chk.ids.count(i) > 1})
assert not dups, f'duplicate ids: {dups}'
missing = sorted(orig_ids - set(chk.ids))
assert not missing, f'missing ids: {missing}'
scripts = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html)
assert sum('function calc()' in s for s in scripts) == 1
app = next(s for s in scripts if 'function calc()' in s)
assert "$('closeSkillPanelModal').onclick" in app
assert app.index('function makeConfigSnapshot()') < app.index('function restoreBaselineConfig(')
for bad in ('fonts.googleapis.com', 'fonts.gstatic.com', 'cloudflareinsights', '__CF$cv$params'):
    assert bad not in html, bad
for needle in ('<style id="embedded-katex">', '<script id="embedded-katex-js">', '<script id="embedded-lucide">'):
    assert html.count(needle) == 1, needle

TARGET.write_text(html, encoding='utf8')
print(f'[build] wrote {TARGET} ({len(html.encode("utf8")):,} bytes; tw-base {len(tw_base):,}, app.css {len(app_css.encode("utf8")):,}, tw-utilities {len(tw_util):,})')
print('[build] extra ids:', sorted(set(chk.ids) - orig_ids))
