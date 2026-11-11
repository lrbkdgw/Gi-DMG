#!/usr/bin/env python3
"""只改表现层的脚本改写器。

读取原版 <script>（/tmp/gi-orig/10_main.js，由 split.py 从提交 2e43850 拆出），仅把渲染模板里的
class 字符串换成 app.css 中定义的语义类；不触碰任何计算与状态逻辑。每条替换都断言出现次数，
源码一旦与预期不符就直接失败，而不是悄悄漂移。输出 /tmp/gi-gen/main.js。
"""
import pathlib
import re
import sys

SRC = pathlib.Path('/tmp/gi-orig/10_main.js')
OUT = pathlib.Path('/tmp/gi-gen'); OUT.mkdir(exist_ok=True)
src = SRC.read_text(encoding='utf8')
n_rules = n_hits = 0


def rep(old, new, count=1):
    global src, n_rules, n_hits
    n = src.count(old)
    if n != count:
        raise SystemExit(f'[codemod] expected {count} occurrence(s) but found {n}:\n  {old[:170]}')
    src = src.replace(old, new)
    n_rules += 1; n_hits += count


def cls(old, new, count=1):
    """替换整个 class 属性值；new 为空串时去掉 class 属性。"""
    rep(f' class="{old}"', f' class="{new}"' if new else '', count)


# ------------------------------------------------------------------ 侧栏：队伍 / 共鸣
cls('text-[12px] text-[#89929d] px-2 py-3', 'sidebar-empty')
cls("sidebar-character-element border ${e?.c||''}", "sidebar-character-element ${e?.c||''}")
cls('chip text-[10.5px] resonance-chip', 'chip resonance-chip')
cls('text-[#aa8a6a]', 't-3')

# ------------------------------------------------------------------ 通用效果行
cls("bg-white/60 border ${effValid(ef)?'border-[#e6d7c0]':'border-[#d95f4a]'} rounded-lg px-2 py-1 text-[11px]",
    "eff-row ${effValid(ef)?'':'is-invalid'}", 2)
cls('grid grid-cols-12 gap-1 items-center', 'grid grid-cols-12 gap-1.5 items-center', 2)
for span, cnt in ((2, 5), (5, 1), (3, 1), (4, 1)):
    cls(f'pi col-span-{span} !text-[10.5px] !px-1 h-6 !py-0', f'pi sm col-span-{span}', cnt)
rep('<button data-ged="${prefix}:${idx}" class="text-[#b86a4a] col-span-1 text-center font-bold cursor-pointer">✕</button>',
    '<button type="button" data-ged="${prefix}:${idx}" class="icon-x col-span-1" title="移除效果" aria-label="移除效果">✕</button>', 2)
cls('col-span-2 text-[10px] text-center text-[#a35a55] bg-[#faeef1] rounded py-0.5', 'col-span-2 eff-fixed-target')

# ------------------------------------------------------------------ 角色编辑器
cls('flex items-start justify-between gap-2 mb-3', 'editor-head')
cls('grid grid-cols-3 gap-2 flex-1', 'grid grid-cols-3 gap-3 flex-1')
rep('<label class="text-[11px]">', '<label>', 3)
cls('pi mt-0.5 font-[600]', 'pi mt-1.5 font-semibold')
cls('pi mt-0.5', 'pi mt-1.5', 36)
rep('<button id="delChar" class="bgh text-[#b65a3a] text-[11px]">删除</button>',
    '<button type="button" id="delChar" class="bgh danger">删除</button>')
cls('flex items-center justify-between mb-2', 'editor-section-head', 3)
cls('config-section-title text-[12px] font-[700] text-[#5a3f28]', 'config-section-title')
cls('config-section-title font-[700] text-[13px]', 'config-section-title', 2)
rep('<button id="toggleQuickSetter" class="text-[11px] text-[#b37a2c] hover:underline cursor-pointer">',
    '<button type="button" id="toggleQuickSetter" class="link-btn">')
cls('hidden bg-[#f3ede1] border border-[#d9cdb6] rounded-xl p-3 mb-4 space-y-3 text-[11px]', 'qs-box hidden')
cls('grid grid-cols-4 gap-2 text-[11.5px] mb-2', 'grid grid-cols-4 gap-3 mb-3', 2)
cls('grid grid-cols-3 gap-2 text-[11.5px] mb-2', 'grid grid-cols-3 gap-3 mb-3', 2)
cls('text-[11px] font-[600] text-[#7a6248] mt-1 mb-1', 'field-group-label')
cls('grid grid-cols-4 gap-1.5 text-[11px]', 'grid grid-cols-4 gap-3')
cls('text-center element-stat-field', 'element-stat-field')
cls('pi text-center', 'pi')
cls('mt-2 p-2 bg-[#fcf8ef] rounded-lg text-[11px] text-[#5a4030]', 'stat-strip mt-4')
rep('<div id="equippedEffectsBox" class="mt-2"></div>', '<div id="equippedEffectsBox" class="equip-list mt-2"></div>')
rep('<button id="addDmgBtn" class="bs-ico sm" title="添加伤害来源" aria-label="添加伤害来源">',
    '<button type="button" id="addDmgBtn" class="bs-ico sm" title="添加伤害来源" aria-label="添加伤害来源" aria-haspopup="menu">')
cls('hidden absolute right-0 top-full mt-1 bg-[#fcf9f2] border border-[#d9cdb6] rounded-xl shadow-lg z-20 p-1.5 flex flex-col gap-0.5 min-w-[128px]',
    'menu hidden')
for bid in ('addDmgN', 'addDmgT', 'addDmgLD', 'addDmgLR'):
    rep(f'<button id="{bid}" class="bs !py-0.5 !px-2 !text-[10px] cursor-pointer">', f'<button type="button" id="{bid}" class="menu-item">')
# 原版用 `#studioMain #dmgList{max-height:none!important;overflow:visible!important}` 抵消了这里的内滚动，
# 新版直接去掉这组类：两个列表随工作区整体滚动。
cls('space-y-2.5 max-h-[520px] overflow-auto pr-1 thin-scroll', 'space-y-3', 2)
rep('<button id="addTalent" class="bs-ico sm cursor-pointer"', '<button type="button" id="addTalent" class="bs-ico sm"')
rep('<button id="qsAddWeaponTal" class="bs-ico sm cursor-pointer"', '<button type="button" id="qsAddWeaponTal" class="bs-ico sm"')
rep('<button id="qsAddArtSet" class="bs-ico sm cursor-pointer"', '<button type="button" id="qsAddArtSet" class="bs-ico sm"')

# ------------------------------------------------------------------ 伤害来源卡片
rep("const borderCls=dmgSourceIncomplete(d)?'border-[#d95f4a]':'border-[#e0cfb7]';", "const borderCls=dmgSourceIncomplete(d)?'is-invalid':'';")
cls('rounded-xl border ${borderCls} bg-[#fcf8ef] p-2.5', 'src-card rounded-xl ${borderCls}', 4)
cls('flex items-center gap-1.5 mb-1.5', 'card-head', 9)
cls('pi font-normal', 'pi font-medium', 5)
rep(' class="text-[10px] text-[#b86a4a]"', ' type="button" class="link-btn danger"', 5)
cls('grid grid-cols-3 gap-1.5 text-[11px]', 'grid grid-cols-3 gap-3', 4)
cls('col-span-3 pt-1.5 mt-1 border-t border-[#e8dcc8] grid grid-cols-3 gap-1.5 text-[10.5px]', 'col-span-3 src-card-foot grid grid-cols-3 gap-3')
cls('pi mt-0.5 !py-0 h-6 !text-[10px]', 'pi sm mt-1.5')
cls('col-span-2 text-[10px] text-[#93785d] self-end', 'col-span-2 self-end field-hint')
rep(' class="chip !text-[10.5px] !py-1 contrib-chip ', ' class="chip contrib-chip ')
cls('ml mb-1', 'ml mb-1.5')
cls('flex flex-wrap gap-1', 'flex flex-wrap gap-1.5')
cls('text-[10px] text-[#a08360]', 'list-empty', 9)
cls('text-[11px] text-[#a08360]', 'list-empty', 2)

# ------------------------------------------------------------------ 天赋卡片
cls('flex items-center justify-between text-[10.5px] bg-[#f7eedc] px-2 py-1 rounded-md mb-1.5 gap-2', 'info-bar mb-3')
cls('text-[#8a7661]', 't-2', 3)
cls('text-[#93785d]', '', 3)
cls("rounded-xl border ${valid?'border-[#e0cfb7]':'border-[#d95f4a]'} bg-[#fcf8ef] p-2.5", "src-card rounded-xl ${valid?'':'is-invalid'}")
rep(' class="mt-1.5 text-[11px] text-[#b07a33] font-[600] cursor-pointer"', ' type="button" class="link-btn mt-2.5"')

# ------------------------------------------------------------------ 快捷配置助手
cls('bg-white/40 rounded-lg p-2', 'qs-section')
cls("bg-white/40 rounded-lg p-2 ${wInvalid?'qs-details-invalid':''}", "qs-section ${wInvalid?'is-invalid':''}")
cls("bg-white/40 rounded-lg p-2 ${aInvalid?'qs-details-invalid':''}", "qs-section ${aInvalid?'is-invalid':''}")
cls('flex items-center justify-between gap-2 cursor-pointer font-[700] text-[#5a4030] text-[12px]', 'qs-summary', 3)
cls('mt-2 space-y-2', 'qs-body', 3)
cls('grid grid-cols-3 gap-2', 'grid grid-cols-3 gap-3', 4)
cls('grid grid-cols-3 gap-1', 'grid grid-cols-3 gap-3')
cls('pi mt-0.5 h-7 !py-0', 'pi sm mt-1.5', 25)
cls('bs-cap !py-0.5 !px-2.5 !text-[10px] cursor-pointer', 'bs xs', 2)
rep('<div class="flex items-center justify-between"><span class="font-[600] text-[#7a6248]">武器天赋</span>', '<div class="qs-subhead"><span>武器天赋</span>')
rep('<div class="flex items-center justify-between"><span class="font-[600] text-[#7a6248]">套装天赋效果</span>', '<div class="qs-subhead"><span>套装天赋效果</span>')
cls('font-[600] text-[#7a6248]', 'field-group-label', 2)
rep('<button id="qsApply" class="bs-cap !py-1.5 !px-3 !text-[11.5px] w-full mt-2 cursor-pointer">', '<button type="button" id="qsApply" class="bg w-full">')
cls("bg-white/50 rounded-lg p-2 border ${(t.effs||[]).some(ef=>!effValid(ef))?'border-[#d95f4a]':'border-[#d9cdb6]'}",
    "sub-card ${(t.effs||[]).some(ef=>!effValid(ef))?'is-invalid':''}", 2)
cls("bg-white/50 rounded p-2 border ${(s.effs||[]).some(ef=>!effValid(ef))?'border-[#d95f4a]':'border-[#d9cdb6]'}",
    "sub-card ${(s.effs||[]).some(ef=>!effValid(ef))?'is-invalid':''}", 2)
cls('pi !text-[10.5px] h-6 !py-0', 'pi sm')
cls('pi !text-[10.5px] h-6 !py-0 flex-1', 'pi sm flex-1', 3)
rep(' class="text-[10px] text-[#b86a4a] cursor-pointer"', ' type="button" class="link-btn danger"', 4)
cls('flex items-center justify-between mb-1.5 text-[10.5px] bg-[#f7eedc] px-2 py-1 rounded-md gap-2', 'info-bar mb-2', 2)
cls('space-y-1', 'space-y-1.5', 4)
rep(' class="mt-1.5 text-[10.5px] text-[#b07a33] cursor-pointer"', ' type="button" class="link-btn mt-2"', 2)
rep(' class="text-[10.5px] text-[#b07a33] whitespace-nowrap cursor-pointer"', ' type="button" class="link-btn whitespace-nowrap"', 2)

# ------------------------------------------------------------------ 已装备效果摘要
cls('rounded-lg border border-[#b8c1de] bg-[#eef1fa] p-2 mb-1.5', 'equip-card')
rep('<div class="text-[10.5px] font-[700] text-[#3a55a3] mb-0.5">⚔ 武器</div>', '<div class="equip-title">武器</div>')
cls('text-[10.5px] text-[#4a5a80]', 'equip-line')
cls('text-[10.5px] text-[#4a5a80] mt-0.5', 'equip-line', 3)
cls('rounded-lg border border-[#deb8c1] bg-[#faeef1] p-2', 'equip-card')
rep('<div class="text-[10.5px] font-[700] text-[#a35a55] mb-0.5">⬡ 圣遗物</div>', '<div class="equip-title">圣遗物</div>')
cls('text-[10.5px] text-[#7c4a50]', 'equip-line')
cls('text-[10.5px] text-[#7c4a50] mt-0.5', 'equip-line', 2)

# ------------------------------------------------------------------ 伤害统计列表
cls('text-[12px] text-[#a18360]', 'list-empty')
cls('text-[10.5px] text-[#8a7661] font-normal', 'res-note')
cls('text-[10px] text-[#8f5fa3]', 'tag', 2)
cls('pill bg-stone-100 text-stone-600 border-stone-300 text-[9.5px]', 'pill is-instant')
cls('pill bg-amber-100 text-amber-700 border-amber-300 text-[9.5px]', 'pill is-snapshot')
cls('pill bg-sky-100 text-sky-700 border-sky-300 text-[9.5px]', 'pill is-dynamic')
cls('sc rounded-[14px] p-2.5 cursor-pointer hover:border-[#c89a4b] transition relative group', 'res-card')
rep('<div class="flex items-center justify-between"><div class="text-[12px] font-[700] flex items-center gap-1.5 flex-wrap">${labelName} · <span class="font-normal">${r.dName}</span>${typeTag}${timingTag}</div>${elementBadge(r.elem,false,\'result-element-badge\')}</div>',
    '<div class="res-head">${elementBadge(r.elem,false,\'result-element-badge\')}<div class="res-title">${labelName} · <span class="res-src">${r.dName}</span>${typeTag}${timingTag}</div></div>')
cls('mt-1 flex items-baseline justify-between', 'res-value-row')
rep('<div class="text-[11px] text-[#81644a]">总期望 <b class="text-[#2d2319] text-[14px]">', '<div class="res-value">总期望 <b>')
cls('text-[10px] text-[#b37a2c] opacity-0 group-hover:opacity-100 transition', 'res-hint')
cls('text-[10.5px] text-[#9a7b5a]', 'res-sub', 5)

# ------------------------------------------------------------------ 时间编排
rep('<button type="button" class="bs" data-tle-grp ', '<button type="button" class="bs xs" data-tle-grp ', 2)
rep('<button type="button" class="bs" data-tle-copy=', '<button type="button" class="bs sm" data-tle-copy=')
rep('<button type="button" class="bgh" data-tle-remove=', '<button type="button" class="bgh sm danger" data-tle-remove=')
rep('<button type="button" class="bs" data-tle-add=', '<button type="button" class="bs sm" data-tle-add=')

# ------------------------------------------------------------------ 技能面板时序解析
cls('grid grid-cols-3 gap-2 bg-white/60 p-2 rounded-lg border border-[#e1d5c2] text-[11px]', 'stat-grid')
cls('chip talent-name-chip text-[10px] !py-0.5', 'chip talent-name-chip')
cls('text-[#a08360] text-[10.5px]', 't-3')
cls('sc rounded-xl p-2.5 space-y-1.5 border border-[#dcd0bb]', 'detail-phase')
cls('flex items-center justify-between flex-wrap gap-1', 'detail-phase-head')
cls('font-[700] text-[#5a4030] text-[11.5px] flex items-center gap-1.5', 'detail-phase-title')
cls('w-2 h-2 rounded-full bg-[#c89a4b]', 'detail-dot')
cls('pill bg-amber-100 text-amber-800 border-amber-300 text-[9.5px]', 'pill is-snapshot')
cls('pill bg-sky-100 text-sky-800 border-sky-300 text-[9.5px]', 'pill is-dynamic')
cls('text-[10.5px] text-[#7a6452] flex items-center gap-1 flex-wrap', 'detail-talents')
cls('font-[600]', 'detail-talents-label')
cls('sc rounded-xl p-2.5 space-y-1 bg-[#f5ecdd] border border-[#d9ccb5]', 'detail-summary')
cls('flex items-center justify-between text-[12px] font-[700] text-[#3e2e1e]', 'detail-summary-head')
cls('text-[#c89a4b]', '', 2)
cls('text-[11px] text-[#7a6652]', 'detail-summary-sub')
cls('text-[11px] text-[#8a7050] font-[600]', 'detail-caption')

# ------------------------------------------------------------------ 基准值 / 拉表方案
cls('text-[#a07e59] py-1 text-[11.5px]', 'list-empty', 2)
cls('flex justify-between items-center bg-[#fcf9f2] border border-[#d7c9b3] p-2 rounded-lg', 'base-row', 2)
rep("clz=diff>0?'text-emerald-600':(diff<0?'text-rose-600':'text-gray-500');", "clz=diff>0?'t-success':(diff<0?'t-danger':'t-3');")
rep('<button class="font-semibold text-[#5a4030] hover:underline cursor-pointer" data-viewb=', '<button type="button" class="base-name" title="查看基准快照" data-viewb=')
cls('text-[#8a7661] text-[10.5px]', 'base-val')
cls('font-[700] ${clz} text-[11.5px]', 'base-diff ${clz}')
rep('<button class="text-[#5c7a57] hover:bg-[#e3f0d8] rounded px-1 cursor-pointer" data-loadb=', '<button type="button" class="link-btn" data-loadb=')
rep('<button class="text-[#b86a4a] hover:bg-rose-100 rounded px-1 cursor-pointer" data-delb=', '<button type="button" class="icon-x" title="删除基准" aria-label="删除基准" data-delb=')
cls('text-[11px] font-[600] text-[#5a4030]', 'scheme-char')
cls('text-[11px] text-[#8a7661]', 'scheme-name')
cls('text-[10px] text-[#b37a2c]', 'tag')
rep('<button class="text-[#b86a4a] hover:bg-rose-100 rounded px-1 text-[11px] cursor-pointer" data-qs-del=', '<button type="button" class="icon-x" title="删除方案" aria-label="删除方案" data-qs-del=')

# ------------------------------------------------------------------ 快速拉表：入口文案 / 进度 / 结果表
rep("const qtBtn=$('btnQuickTable');if(qtBtn)qtBtn.textContent='⚡ 快速拉表';", 'setQuickTableLabel(false);')
rep("const qtBtn=$('btnQuickTable');if(qtBtn)qtBtn.textContent=quickTableActive?'✓ 完成拉表':'⚡ 快速拉表';", 'setQuickTableLabel(quickTableActive);')
rep('let qtRunning=false,qtCancelled=false;',
    "// 「更多」菜单中的拉表入口：只更新文字标签，保留按钮内的图标。\n"
    "function setQuickTableLabel(active){\n"
    "const btn=$('btnQuickTable');if(!btn)return;\n"
    "(btn.querySelector('[data-label]')||btn).textContent=active?'完成拉表':'快速拉表';\n"
    "}\n"
    'let qtRunning=false,qtCancelled=false;')
rep("btn.className='bs !py-1 !px-2.5 !text-[11px] !bg-[#e8d5b0] !border-[#c89a4b] !text-[#7a5a20]';", "btn.className='bs sm bs-active';")
rep("btn.className='bs !py-1 !px-2.5 !text-[11px]';", "btn.className='bs sm';")
cls('py-12 px-6 flex flex-col items-center justify-center space-y-4 max-w-md mx-auto text-center', 'progress-box')
cls('inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#faeedd] text-[#c89a4b] mb-1', 'progress-icon')
cls('font-[700] text-[16px] text-[#3a3028]', 'progress-title')
cls('w-full bg-[#ebdcc4] rounded-full h-3.5 overflow-hidden border border-[#d9cdb6] p-0.5 shadow-inner', 'progress-track')
cls('bg-gradient-to-r from-[#d9aa55] to-[#c89a4b] h-full rounded-full transition-all duration-75', 'progress-bar')
cls('flex items-center justify-between w-full text-[12px] text-[#8a7661] font-mono px-1', 'progress-meta')
cls('font-bold text-[#5b4630]', 'progress-pct')
cls('bs !py-1.5 !px-4 !text-[12px] text-[#7a6045] mt-2', 'bs sm')
cls('text-center py-12 text-[#8a7661]', 'list-empty is-center')
cls('w-full min-w-[640px] rounded-2xl overflow-hidden border border-[#d9cdb6] bg-white/50 shadow-sm', 'qt-table-wrap')
cls('w-full text-[12.5px] border-separate border-spacing-0', 'qt-table')
cls('sticky top-0 z-10 px-4 py-3 bg-[#efe3cc] text-[#6b5233] font-[700] text-center whitespace-nowrap border-b border-[#d9cdb6]', '', 3)
cls('sticky top-0 z-10 px-3 py-3 bg-[#e8dac0] text-[#5b4630] font-[700] text-center whitespace-nowrap border-b border-[#d9cdb6]', 'is-share', 2)
rep("const zebra=ri%2?'bg-[#f6efdf]':'bg-[#fcf8ee]';", "const zebra=ri%2?'is-odd':'';")
cls('${zebra} hover:bg-[#f0e3c8] transition-colors', '${zebra}')
cls('px-4 py-3 text-center text-[#8a7050] font-[600] border-b border-[#eee2ca]', 'qt-cost')
cls('px-4 py-3 text-center text-[#5a4030] border-b border-[#eee2ca]', '')
cls('px-4 py-3 text-center border-b border-[#eee2ca]', '')
cls("inline-block rounded-full px-3.5 py-1 text-[12px] font-[700] ${isBest?'bg-[#c89a4b] text-[#fffef9] shadow':'bg-[#efe4cf] text-[#5b4630] border border-[#ddcdb2]'}",
    "qt-dps ${isBest?'is-best':''}")
cls('px-3 py-3 text-center text-[#5a4030] border-b border-[#eee2ca] font-mono text-[11.5px]', 'qt-share')
cls('px-3 py-3 text-center text-[#8a5b28] border-b border-[#eee2ca] font-mono text-[11.5px]', 'qt-share is-reaction')
cls('flex items-center justify-between mb-2 text-[11px] text-[#8a7661]', 'qt-meta')

# ------------------------------------------------------------------ 武器 / 圣遗物库
cls('text-[12px] text-[#a18360] py-2', 'list-empty', 2)
cls('sc rounded-xl p-3', 'lib-item', 2)
cls('font-[700] text-[13px] truncate', 'lib-name', 2)
cls('text-[#c89a4b] text-[11px]', 'lib-stars')
cls('text-[11px] text-[#8a7050]', 'lib-meta')
rep(' class="bs !py-1 !px-2.5 !text-[11px] cursor-pointer" data-wedit=', ' type="button" class="bs sm" data-wedit=')
rep(' class="bg !py-1 !px-3 !text-[11px] cursor-pointer" data-wapply=', ' type="button" class="bg sm" data-wapply=')
rep(' class="bg !py-1 !px-3 !text-[11px] cursor-pointer" data-aapply=', ' type="button" class="bg sm" data-aapply=')
rep(' class="bgh !py-1 !px-2 !text-[11px] cursor-pointer" data-wdel=', ' type="button" class="bgh sm danger" data-wdel=')
rep(' class="bgh !py-1 !px-2 !text-[11px] cursor-pointer" data-adel=', ' type="button" class="bgh sm danger" data-adel=')
cls('flex items-center gap-1 text-[10.5px]', 'lib-duration', 2)
cls('pi !py-0 h-6 !px-1 w-16 !text-[10px]', 'pi sm w-16', 2)

# ------------------------------------------------------------------ 历史记录
rep(' class="bg !py-1 !px-3 !text-[11px] cursor-pointer" data-hist-cfg-load=', ' class="bs sm" data-hist-cfg-load=')
rep(' class="bg !py-1 !px-3 !text-[11px] cursor-pointer" data-hist-qt-view=', ' class="bs sm" data-hist-qt-view=')
rep(' class="bgh !py-1 !px-2 !text-[11px] cursor-pointer" data-hist-del-cfg=', ' class="icon-x" title="删除记录" aria-label="删除记录" data-hist-del-cfg=')
rep(' class="bgh !py-1 !px-2 !text-[11px] cursor-pointer" data-hist-del-qt=', ' class="icon-x" title="删除记录" aria-label="删除记录" data-hist-del-qt=')
cls('bs !py-0.5 !px-2 !text-[10px] cursor-pointer', 'link-btn', 2)

# ------------------------------------------------------------------ 面板明细 / 基准快照 / 公式
cls('text-[13px] text-[#8a7661]', 'detail-note')
cls('text-[#2d2319]', 't-1', 9)
cls('text-center text-[#8a7661] py-4', 'list-empty is-center')
cls('sc rounded-xl p-4 border border-[#d7c9b3]', 'detail-card')
cls('flex items-center gap-2 mb-3 border-b border-[#e1d3bb] pb-2', 'detail-card-head')
cls('font-bold text-[16px]', 'detail-name')
cls('text-[12px] text-[#8a7661]', 'detail-lv')
cls('grid grid-cols-2 md:grid-cols-4 gap-y-3 gap-x-2 text-[12.5px] mb-3', 'detail-stats')
cls('text-[11.5px] text-[#5c4631] mb-2 p-2 bg-white/50 rounded leading-relaxed', 'detail-line', 5)
cls('text-[11.5px] text-[#5c4631] p-2 bg-white/50 rounded leading-relaxed', 'detail-line')
cls('font-bold mr-1.5 text-[#8a7661]', 'detail-label', 6)
cls('mx-1.5 opacity-40', 'detail-sep', 5)
cls('bg-white/50 rounded-lg px-2 py-1.5', 'formula-react')

# ------------------------------------------------------------------ 角色伤害占比
rep("""  pyro: '#d75a3a', hydro: '#2a7fbe', electro: '#7d55c7', cryo: '#3a9db8',
  dendro: '#5a9a3a', anemo: '#2b9b7f', geo: '#b88a2d', physical: '#6a5f57',
  reaction: '#e67e22'""",
    """  pyro: '#e5532d', hydro: '#2a8ae0', electro: '#9461e8', cryo: '#19a9c4',
  dendro: '#62a31a', anemo: '#16ab81', geo: '#d1920a', physical: '#7b7b86',
  reaction: '#e07b16'""")
rep("let color = ELEM_COLOR_MAP[c.element] || '#8a7661';", "let color = ELEM_COLOR_MAP[c.element] || ELEM_COLOR_MAP.physical;")
rep("color: '#e67e22',", 'color: ELEM_COLOR_MAP.reaction,')
rep('fill="#f5ede0" stroke="#dfd2bd" stroke-width="2"/>', 'fill="var(--muted)" stroke="var(--border)" stroke-width="2"/>')
rep('text-anchor="middle" fill="#8a7661" font-size="13" font-weight="600">', 'text-anchor="middle" fill="var(--text-3)" font-size="13" font-weight="500">')
rep('fill="#fcf9f2" style="pointer-events:none" />', 'fill="var(--surface)" style="pointer-events:none" />', 2)
rep('font-size="11.5" fill="#8a7661" font-weight="600" style="pointer-events:none">', 'font-size="11.5" fill="var(--text-3)" font-weight="500" style="pointer-events:none">', 2)
rep('font-size="15" fill="#2e241b" font-weight="700" style="pointer-events:none">', 'font-size="15" fill="var(--text)" font-weight="650" style="pointer-events:none">', 2)
rep('stroke="#fcf9f2" stroke-width="2.5"></path>', 'stroke="var(--surface)" stroke-width="2.5"></path>')
cls('mx-auto drop-shadow-sm', 'mx-auto', 2)
cls('text-center text-[#8a7661] py-8', 'list-empty is-center')
cls('element-badge bg-[#faeedd] text-[#c05621] border-[#fbd38d]', 'element-badge elem-reaction')
cls('text-[11px] text-[#8a7661] mt-1 flex gap-3', 'share-note')
cls('text-[11px] text-[#8a7661] mt-1', 'share-note')
cls('text-[#5a4030]', 't-1', 3)
cls('sc p-3.5 rounded-xl border border-[#d7c9b3] bg-white/60', 'share-card')
cls('flex items-center justify-between mb-1.5', 'share-head')
cls('font-bold text-[14px] text-[#2e241b]', 'share-name')
cls('text-[13px] font-bold font-mono text-[#2e241b]', 'share-dmg')
cls('pill font-mono font-bold text-[11px] px-2 py-0.5', 'pill share-pct')
cls('w-full bg-[#ebdcc4] h-2.5 rounded-full overflow-hidden border border-[#d9cdb6]/40 p-0.5 shadow-inner', 'share-track')
cls('h-full rounded-full transition-all duration-300', 'share-bar')
cls('flex flex-col md:flex-row items-center gap-6 pb-2', 'share-layout')
cls('shrink-0 flex flex-col items-center', 'share-chart')
cls('text-[12px] text-[#8a7661] mt-2 font-mono', 'share-dps')
cls('text-[#c89a4b] font-bold text-[14px]', '')
cls('flex-1 w-full space-y-2.5 max-h-[55vh] overflow-auto thin-scroll pr-1', 'share-list thin-scroll')

# ------------------------------------------------------------------ 跳转高亮
rep("card.classList.add('ring-2', 'ring-[#c89a4b]', 'ring-offset-2');", "card.classList.add('is-flash');")
rep("setTimeout(()=>card.classList.remove('ring-2', 'ring-[#c89a4b]', 'ring-offset-2'), 1600);", "setTimeout(()=>card.classList.remove('is-flash'), 1600);")

# ------------------------------------------------------------------ 收尾自检：不得残留旧配色 / !important 工具类
leftovers = []
for i, line in enumerate(src.split('\n'), 1):
    if len(line) > 20000:
        continue
    for m in re.finditer(r'[a-z:-]*-\[#[0-9a-fA-F]{3,8}\](?:/\d+)?|(?<![\w-])!(?:py|px|text|bg|border)-[\w.\[\]#-]+|\b(?:text|bg|border)-(?:stone|amber|sky|rose|emerald|gray)-\d{2,3}\b|bg-white/\d+', line):
        leftovers.append((i, m.group(0)))
if leftovers:
    for i, tok in leftovers[:40]:
        print(f'[codemod] leftover legacy token at line {i}: {tok}')
    raise SystemExit(f'[codemod] {len(leftovers)} leftover legacy token(s)')

(OUT / 'main.js').write_text(src, encoding='utf8')
print(f'[codemod] ok: {n_rules} rules, {n_hits} replacements -> {OUT / "main.js"}')
