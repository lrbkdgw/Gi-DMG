// 行为一致性校验：对「原版」与「新版」执行同一套确定性操作脚本，逐步比对状态与结算结果。
//   node redesign/qa/parity.mjs [new.html] [orig.html]
// 只使用两版都存在的 id / data-* 选择器；Math.random 由 lib.mjs 以相同种子接管，uid 序列一致。
import { launch, open, sleep, REPO, CFG_DIR } from './lib.mjs';
import fs from 'node:fs';
import path from 'node:path';

const NEW = process.argv[2] || path.join(REPO, 'Gi DMG v2.2.0.html');
const ORIG = process.argv[3] || '/tmp/gi-orig/full.html';
const configs = fs.readdirSync(CFG_DIR).filter(f => f.endsWith('.json')).sort();

/* ---------- 注入页面的工具 ---------- */
function installQA() {
  const q = (sel, i = 0) => { const el = document.querySelectorAll(sel)[i]; if (!el) throw new Error('missing ' + sel + '[' + i + ']'); return el; };
  const fire = el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); };
  window.__qa = {
    click: (sel, i = 0) => q(sel, i).click(),
    count: sel => document.querySelectorAll(sel).length,
    set(sel, v, i = 0) { const el = q(sel, i); el.value = v; fire(el); },
    // 对容器内第 k 个原生控件做一次确定性修改；返回描述（两版应一致）
    poke(rootSel, k) {
      const root = q(rootSel);
      const list = [...root.querySelectorAll('input, select')].filter(e => e.type !== 'file' && !e.disabled);
      if (!list.length) return 'none';
      const el = list[k % list.length];
      let desc;
      if (el.tagName === 'SELECT') {
        const opts = [...el.options].filter(o => !o.disabled);
        if (!opts.length) return 'select-empty';
        const o = opts[(k * 3 + 1) % opts.length];
        el.value = o.value; desc = 'select=' + o.value; fire(el);
      } else if (el.type === 'checkbox') {
        el.checked = !el.checked; desc = 'check=' + el.checked; fire(el);
      } else if (el.type === 'number' || el.type === 'range') {
        const lo = el.min !== '' ? +el.min : 0, hi = el.max !== '' ? +el.max : 60;
        const v = Math.min(hi, lo + ((k * 7) % 23) + 1);
        el.value = String(v); desc = el.type + '=' + v; fire(el);
      } else {
        el.value = '项' + k; desc = 'text=' + el.value; fire(el);
      }
      const keys = Object.keys(el.dataset).filter(x => !/studio/i.test(x)).sort().map(x => x + ':' + el.dataset[x]).join(',');
      return `${el.tagName}[${keys}|${el.id}] ${desc}`;
    },
    snap() {
      const nums = el => el ? ((el.textContent || '').match(/-?\d[\d,]*(?:\.\d+)?/g) || []).join(' ') : null;
      const vals = el => el ? [...el.querySelectorAll('input, select')].filter(e => e.type !== 'file').map(e => (e.type === 'checkbox' ? String(e.checked) : e.value) + (e.disabled ? '!' : '')).join('|') : null;
      const J = v => { try { return JSON.stringify(v, (k, x) => typeof x === 'number' && !Number.isInteger(x) ? +x.toPrecision(12) : x); } catch (e) { return 'ERR ' + e.message; } };
      const lc = window.__lastCalc, g = id => document.getElementById(id);
      const hid = id => { const e = g(id); return !e || e.classList.contains('hidden') ? 1 : 0; };
      return {
        state: J(makeConfigSnapshot()),
        baselines: J((S.baselines || []).map(b => ({ name: b.name, val: b.val, hasCfg: !!b.config }))),
        calcTotal: lc ? J(lc.total) : null,
        calcResults: lc ? J(lc.results) : null,
        calcShares: lc ? J(lc.shares || null) : null,
        total: g('totalDmg').textContent.trim(),
        dps: hid('dpsStatRow') ? '(hidden)' : g('totalDps').textContent.trim(),
        resN: g('resList').children.length, res: nums(g('resList')),
        baseTitle: g('baseSectionTitle').textContent.trim(), addBase: g('addBaseBtn').textContent.trim(), baseList: nums(g('baseList')),
        chars: g('charList').querySelectorAll('[data-ch]').length,
        charNames: [...g('charList').querySelectorAll('[data-ch]')].map(e => e.getAttribute('aria-label')).join('|'),
        reso: (g('resonanceBox').textContent || '').replace(/\s+/g, ''),
        editorHidden: hid('editorContent'), emptyHidden: hid('editorEmpty'),
        editor: vals(g('editorContent')),
        cards: [g('dmgList') ? g('dmgList').children.length : -1, g('talentList') ? g('talentList').children.length : -1].join('/'),
        fs: nums(g('finalStatsDisplay')), eq: nums(g('equippedEffectsBox')),
        tle: vals(g('timelineEditor')),
        tlState: [hid('timelineDisabledState'), hid('timelineContainer')].join('/'),
        tlBadges: ['tlRotDurBadge', 'tlTotalDmgBadge', 'tlDpsBadge'].map(id => g(id).textContent.trim()).join('|'),
        tlNodes: [...g('timelineGraph').querySelectorAll('button')].map(b => b.title + '@' + b.getAttribute('style')).join('|'),
        monster: vals(g('monsterWorkspace')),
        qt: quickTableActive, qtBanner: hid('qtModeBanner'), shareBtn: hid('btnShowDmgShare'),
        ws: g('genshinView').dataset.workspace || '',
        panels: ['characterWorkspace', 'monsterWorkspace', 'timelineWorkspace'].map(hid).join(''),
        modals: [...document.querySelectorAll('.modal-overlay')].filter(m => !m.classList.contains('hidden')).map(m => m.id).join(','),
      };
    },
    modalNums: id => ((document.getElementById(id).textContent || '').match(/-?\d[\d,]*(?:\.\d+)?/g) || []).join(' '),
  };
}

/* ---------- 操作脚本 ---------- */
async function run(file, tag) {
  const browser = await launch();
  const page = await open(browser, file, { seed: 7, quiet: true });
  const dialogs = [];
  page.on('dialog', async d => { dialogs.push(d.type() + ':' + d.message()); await d.accept(d.type() === 'prompt' ? (d.defaultValue() || '1') : undefined); });
  await page.evaluate(installQA);
  const log = [];
  const snap = async (label, extra) => { await sleep(40); log.push({ label, ...(await page.evaluate(() => __qa.snap())), dialogs: dialogs.length, ...(extra || {}) }); };
  const ev = (fn, ...a) => page.evaluate(fn, ...a);
  const click = async (sel, i = 0) => ev((s, i) => __qa.click(s, i), sel, i);
  const set = async (sel, v, i = 0) => ev((s, v, i) => __qa.set(s, v, i), sel, v, i);
  const count = sel => ev(s => __qa.count(s), sel);
  const pokeAll = async (label, rootSel, n, step = 1) => {
    for (let k = 0; k < n; k += step) {
      const desc = await ev((r, k) => __qa.poke(r, k), rootSel, k);
      await snap(`${label} poke#${k}`, { desc });
    }
  };
  const closeModals = async () => ev(() => document.querySelectorAll('.modal-overlay').forEach(m => { if (!m.classList.contains('hidden')) toggleModal(m.id, false); }));
  // 走真实的「导入配置」文件框。无头浏览器的 setFileInputFiles 不认非 ASCII 路径，先复制成 ASCII 文件名。
  const importCfg = async name => {
    const tmp = `/tmp/qa_cfg/${configs.indexOf(name)}.json`;
    fs.mkdirSync('/tmp/qa_cfg', { recursive: true }); fs.copyFileSync(CFG_DIR + name, tmp);
    await ev(() => { window.__imported = false; document.getElementById('importFile').addEventListener('change', () => { window.__imported = true; }, { once: true, capture: true }); });
    const input = await page.$('#importFile');
    await input.uploadFile(tmp);
    await sleep(350);
    const want = JSON.parse(fs.readFileSync(CFG_DIR + name, 'utf8')).chars.length;
    const got = await ev(() => ({ fired: window.__imported, n: S.chars.length }));
    if (!got.fired || got.n !== want) throw new Error(`import of ${name} did not take effect (${JSON.stringify(got)}, want ${want})`);
  };
  try {
    await snap('fresh');

    /* A. 五份示例配置：导入、切换角色 / 工作区、三个只读弹窗 */
    for (const name of configs) {
      await importCfg(name);
      await snap(`import ${name}`);
      const n = await count('#charList [data-ch]');
      for (let i = 0; i < n; i++) { await click('#charList [data-ch]', i); await snap(`${name} char#${i}`); }
      await click('#navMonster'); await snap(`${name} nav monster`);
      await click('#navTimeline'); await snap(`${name} nav timeline`);
      await click('#navCharacters'); await snap(`${name} nav chars`);
      await click('#btnShowDetails'); await snap(`${name} details`, { modal: await ev(() => __qa.modalNums('detailModalContent')) });
      await closeModals();
      const rn = await count('#resList [data-inspect]');
      for (let i = 0; i < Math.min(rn, 4); i++) {
        await click('#resList [data-inspect]', i);
        await snap(`${name} inspect#${i}`, { modal: await ev(() => __qa.modalNums('skillModalContent')), title: await ev(() => document.getElementById('skillModalTitle').textContent.replace(/\s+/g, '')) });
        await closeModals();
      }
      if (await ev(() => !document.getElementById('btnShowDmgShare').classList.contains('hidden'))) {
        await click('#btnShowDmgShare'); await snap(`${name} share`, { modal: await ev(() => __qa.modalNums('dmgShareModalContent')) });
        await closeModals();
      }
    }

    /* B. 编辑器全流程（时间轴开启的配置） */
    await importCfg('Vesna v3.1.6.json'); await snap('B import');
    await click('#charList [data-ch]', 0);
    for (const [f, v] of [['baseAtk', '412'], ['weaponAtk', '608'], ['atkPct', '46.6'], ['critRate', '71.5'], ['critDMG', '188'], ['em', '240'], ['lv', '80'], ['name', '测试角色'], ['allDmgBonus', '12']]) {
      await set(`#editorContent [data-f="${f}"]`, v); await snap(`B set ${f}`);
    }
    await set('#editorContent [data-eb="anemo"]', '15'); await snap('B set eb');
    await set('#editorContent select[data-f="element"]', 'pyro'); await snap('B element pyro');
    await set('#editorContent select[data-f="element"]', 'anemo'); await snap('B element anemo');
    await click('#charList [data-tc]', 1); await snap('B char1 off');
    await click('#charList [data-tc]', 1); await snap('B char1 on');
    for (const id of ['addDmgN', 'addDmgT', 'addDmgLD', 'addDmgLR']) { await click('#' + id); await snap('B ' + id); }
    await pokeAll('B dmgList', '#dmgList', 150);
    const nc = await count('#dmgList [data-contrib]');
    for (let i = 0; i < Math.min(nc, 6); i++) { await click('#dmgList [data-contrib]', i); await snap(`B contrib#${i}`); }
    await click('#addTalent'); await snap('B addTalent');
    for (let i = 0; i < 4; i++) { await click('#talentList [data-ae]', (await count('#talentList [data-ae]')) - 1); await snap(`B addEff#${i}`); }
    await pokeAll('B talentList', '#talentList', 120);
    await click('#talentList [data-tt]', 0); await snap('B talent toggle');
    await click('#talentList [data-ged]', 0); await snap('B eff remove');
    await click('#talentList [data-td]', 1); await snap('B talent delete');
    await click('#dmgList [data-dd]', 2); await snap('B dmg delete');
    await click('#toggleQuickSetter'); await snap('B qs open');
    await pokeAll('B quickSetter', '#quickSetter', 90);
    for (const sel of ['#qsAddWeaponTal', '#qsAddArtSet', '[data-qs-add-set-eff]', '[data-wt-ae]', '[data-qs-set-on]', '[data-wt-on]']) {
      if (await count('#quickSetter ' + sel)) { await click('#quickSetter ' + sel, 0); await snap('B qs click ' + sel); }
    }
    await pokeAll('B quickSetter2', '#quickSetter', 60, 3);
    await click('#qsApply'); await snap('B qs apply');
    await click('#toggleQuickSetter'); await snap('B qs close');
    await click('#navMonster'); await snap('B nav monster');
    await pokeAll('B monster', '#monsterWorkspace', 9);
    await click('#navTimeline'); await snap('B nav timeline');
    await pokeAll('B tle', '#timelineEditor', 70);
    for (const sel of ['[data-tle-add]', '[data-tle-copy]', '[data-tle-remove]', '[data-tle-grp]', 'button[data-tle]']) {
      const n = await count('#timelineEditor ' + sel);
      for (const i of [0, Math.floor(n / 2), n - 1].filter((v, k, a) => v >= 0 && v < n && a.indexOf(v) === k)) {
        if (i < await count('#timelineEditor ' + sel)) { await click('#timelineEditor ' + sel, i); await snap(`B tle ${sel}#${i}`); }
      }
    }
    const nb = await count('#timelineGraph button');
    if (nb) { await click('#timelineGraph button', nb - 1); await snap('B graph node click'); }
    await click('#navCharacters'); await snap('B back to chars');

    /* C. 新增 / 删除角色 */
    await click('#addCharBtn'); await snap('C add char');
    await click('#charList [data-ch]', (await count('#charList [data-ch]')) - 1); await snap('C select new');
    await click('#addDmgN'); await pokeAll('C new dmg', '#dmgList', 12);
    await click('#delChar'); await snap('C delete char');

    /* D. 基准值 */
    await click('#addBaseBtn'); await snap('D add baseline');
    await set('#editorContent [data-f="critRate"]', '33'); await snap('D change after baseline');
    await click('#addBaseBtn'); await snap('D add baseline 2');
    await click('#baseList [data-viewb]', 0); await snap('D view baseline', { modal: await ev(() => __qa.modalNums('detailModalContent')) });
    await closeModals();
    await click('#baseList [data-loadb]', 0); await snap('D load baseline');
    await click('#baseList [data-delb]', 1); await snap('D delete baseline');

    /* E. 全局设置 */
    await click('#btnSettings'); await snap('E settings open');
    await click('#cfgTimelineToggle'); await snap('E timeline toggle off');
    await click('#btnSaveSettings'); await snap('E saved (timeline off)');
    await click('#navTimeline'); await snap('E timeline disabled view');
    await click('#btnEnableTimeline'); await snap('E enable from empty state');
    await click('#cfgTimelineToggle'); await set('#cfgRotDurInput', '24'); await click('#cfgDmgShareToggle');
    await set('#cfgHistCountInput', '3'); await set('#qtHistCountInput', '4');
    if (await count('#baseModeBtn')) await click('#baseModeBtn');
    await snap('E settings edited');
    await click('#btnSaveSettings'); await snap('E saved (rot 24)');
    await click('#btnOpenTimelineSettings'); await snap('E open via timeline button'); await closeModals();
    await click('#navCharacters'); await snap('E back');
    await click('#btnSettings'); await click('#cfgTimelineToggle'); await click('#btnSaveSettings'); await snap('E timeline off again');
    const ndt = await count('#dmgList [data-dt]');
    for (let i = 0; i < Math.min(ndt, 3); i++) { await click('#dmgList [data-dt]', i); await snap(`E src toggle#${i}`); }
    await click('#btnSettings'); await click('#cfgTimelineToggle'); await click('#btnSaveSettings'); await snap('E timeline on again');

    /* F. 武器 / 圣遗物库 */
    await click('#toggleQuickSetter'); await click('#qsPickWeapon'); await snap('F weapon mgr');
    await click('#wAddToggle'); await set('#wNewName', '雾切之回光'); await set('#wNewRarity', '5');
    await click('#wAddTal'); await snap('F weapon talent');
    await pokeAll('F weapon form', '#wAddForm', 24);
    await click('#wNewConfirm'); await snap('F weapon saved', { lib: await ev(() => __qa.modalNums('weaponLibList')) });
    if (await count('#weaponLibList [data-wedit]')) { await click('#weaponLibList [data-wedit]', 0); await snap('F weapon edit'); await click('#wEditCancel'); await snap('F weapon edit cancel'); }
    if (await count('#weaponLibList [data-wapply]')) { await click('#weaponLibList [data-wapply]', 0); await snap('F weapon applied'); }
    await closeModals();
    await click('#qsPickArtifact'); await snap('F artifact mgr');
    await click('#aAddToggle'); await set('#aNewName', '绝缘之旗印'); await click('#aNewAddSet'); await snap('F artifact set');
    await pokeAll('F artifact form', '#aAddForm', 20);
    await click('#aNewConfirm'); await snap('F artifact saved', { lib: await ev(() => __qa.modalNums('artifactLibList')) });
    if (await count('#artifactLibList [data-aapply]')) { await click('#artifactLibList [data-aapply]', 0); await snap('F artifact applied'); }
    await closeModals();
    if (await count('#weaponLibList [data-wdel]')) { await click('#qsPickWeapon'); await click('#weaponLibList [data-wdel]', 0); await snap('F weapon deleted'); await closeModals(); }

    /* G. 快速拉表 */
    await click('#btnQuickTable'); await snap('G qt on');
    await click('#addBaseBtn'); await snap('G scheme 1');
    await set('#editorContent [data-f="critRate"]', '80'); await set('#editorContent [data-f="critDMG"]', '150'); await snap('G tweak');
    await click('#addBaseBtn'); await snap('G scheme 2');
    await click('#charList [data-ch]', 1); await set('#editorContent [data-f="em"]', '500'); await click('#addBaseBtn'); await snap('G scheme 3 (char 2)');
    await click('#baseList [data-qs-del]', 0); await snap('G scheme delete');
    await click('#addBaseBtn'); await snap('G scheme 4');
    await click('#qtFinishBtn');
    for (let i = 0; i < 100 && await ev(() => qtRunning); i++) await sleep(100);
    await sleep(200);
    const qtDump = () => ev(() => ({ table: __qa.modalNums('qtTableWrap'), rows: document.querySelectorAll('#qtTableWrap tbody tr').length, results: JSON.stringify(quickTableResults.map(r => [r.cost, Math.round(r.total), Math.round(r.dps || 0)])), sortCost: document.getElementById('qtSortCost').textContent, sortDmg: document.getElementById('qtSortDmg').textContent, prune: document.getElementById('qtPrune').textContent }));
    await snap('G qt results', await qtDump());
    for (const id of ['qtSortDmg', 'qtSortDmg', 'qtSortCost', 'qtSortCost', 'qtPrune', 'qtToggleDmgShareBtn', 'qtPrune']) { await click('#' + id); await snap('G ' + id, await qtDump()); }
    await closeModals(); await snap('G closed');

    /* H. 历史记录、重置、公式 */
    await click('#navHistory'); await snap('H history', { modal: await ev(() => document.querySelectorAll('#historyModalContent [data-hist-qt-view]').length + '/' + document.querySelectorAll('#historyModalContent [data-hist-cfg-load]').length) });
    if (await count('#historyModalContent [data-hist-qt-view]')) { await click('#historyModalContent [data-hist-qt-view]', 0); await snap('H view qt record', await qtDump()); }
    await closeModals();
    await click('#btnReset'); await snap('H reset');
    await click('#btnFormula'); await set('#fLvSlider', '60');
    await snap('H formula', { modal: await ev(() => document.getElementById('fLvVal').textContent + '|' + document.getElementById('fCoeff').textContent + '|' + __qa.modalNums('fReactGrid')) });
    await closeModals();

    /* I. 其余配置上再跑一轮编辑（普通伤害 / 增幅反应 / 旧版月曜来源） */
    for (const name of ['火神.json', '月绽放 2.json', '温迪 2.json', 'Mitya v3.2.1.json']) {
      await importCfg(name); await snap(`I import ${name}`);
      await click('#charList [data-ch]', 0);
      await pokeAll(`I ${name} dmg`, '#dmgList', 60, 2);
      await pokeAll(`I ${name} tal`, '#talentList', 60, 2);
      await click('#toggleQuickSetter'); await pokeAll(`I ${name} qs`, '#quickSetter', 45, 2);
      await click('#navTimeline'); await pokeAll(`I ${name} tle`, '#timelineEditor', 30, 2);
      await click('#navCharacters');
    }
  } catch (e) {
    console.log(`[${tag}] scenario aborted after "${log.length ? log[log.length - 1].label : '-'}": ${String(e.message).split('\n')[0]}`);
    console.log('  dialogs tail:', dialogs.slice(-3), 'errors:', page.__errors.filter(x => !/ERR_/.test(x)).slice(-3));
    await browser.close();
    process.exit(2);
  }
  const errors = page.__errors.filter(x => !/net::ERR_/.test(x));
  await browser.close();
  return { log, dialogs, errors };
}

const a = await run(ORIG, 'orig');
const b = await run(NEW, 'new');
let bad = 0;
const strip = s => String(s).replace(/完成拉表|快速拉表/g, '');
const n = Math.max(a.log.length, b.log.length);
for (let i = 0; i < n; i++) {
  const x = a.log[i], y = b.log[i];
  if (!x || !y) { console.log(`step ${i}: missing in ${x ? 'new' : 'orig'}`); bad++; continue; }
  for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) {
    if (JSON.stringify(x[k]) !== JSON.stringify(y[k])) {
      bad++;
      if (bad <= 25) console.log(`MISMATCH step ${i} [${x.label}] field ${k}\n   orig: ${String(JSON.stringify(x[k])).slice(0, 300)}\n   new : ${String(JSON.stringify(y[k])).slice(0, 300)}`);
    }
  }
}
const da = a.dialogs.map(strip), db = b.dialogs.map(strip);
if (JSON.stringify(da) !== JSON.stringify(db)) { bad++; console.log('DIALOG MISMATCH', JSON.stringify(a.dialogs).slice(0, 600), JSON.stringify(b.dialogs).slice(0, 600)); }
const totals = new Set(a.log.map(s => s.total)), states = new Set(a.log.map(s => s.state));
console.log(`steps compared: ${a.log.length} (orig) / ${b.log.length} (new); dialogs ${a.dialogs.length}/${b.dialogs.length}; distinct totals ${totals.size}; distinct states ${states.size}`);
console.log(`page errors: orig ${a.errors.length}, new ${b.errors.length}`, a.errors.slice(0, 3), b.errors.slice(0, 3));
console.log(bad ? `FAILED: ${bad} mismatch(es)` : 'PARITY OK');
process.exit(bad ? 1 : 0);
