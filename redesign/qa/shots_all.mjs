// 全量截图巡检：node qa/shots_all.mjs <html> <outdir> [dark|-] [W] [H]
import { launch, open, loadConfig, shot, sleep } from './lib.mjs';
import fs from 'node:fs';
const [file, out, themeArg, W = 1440, H = 900] = process.argv.slice(2);
const theme = themeArg === 'dark' ? 'dark' : null;
fs.mkdirSync(out, { recursive: true });
const browser = await launch();
const page = await open(browser, file, { seed: 42, theme, quiet: true, width: +W, height: +H });
page.on('dialog', async d => { await d.accept(d.type() === 'prompt' ? (d.defaultValue() || '1') : undefined); });
const fails = [];
// 每张截图后做一次版面体检：横向溢出、越出视口的元素、被静默裁切的内容、越出视口的弹窗
const AUDIT = () => {
  const de = document.documentElement, vw = de.clientWidth, vh = window.innerHeight, issues = [], seen = new Set();
  const add = (k, extra) => { if (!seen.has(k)) { seen.add(k); issues.push(extra ? `${k} ${extra}` : k); } };
  if (de.scrollWidth > de.clientWidth + 1) add('DOC-OVERFLOW', `${de.scrollWidth}>${de.clientWidth}`);
  const desc = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '');
  const scrollsX = el => { for (let p = el.parentElement; p; p = p.parentElement) { const ox = getComputedStyle(p).overflowX; if (ox === 'auto' || ox === 'scroll') return true; } return false; };
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('svg') || el.closest('.katex')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    if (el.closest('.hidden')) continue;
    if ((r.right > vw + 1 || r.left < -1) && !scrollsX(el)) add('OUT ' + desc(el), `[${Math.round(r.left)},${Math.round(r.right)}] vw=${vw}`);
    if ((cs.overflowX === 'hidden' || cs.overflowX === 'clip') && el.scrollWidth > el.clientWidth + 1 && cs.textOverflow !== 'ellipsis' && cs.position !== 'absolute') add('CLIP ' + desc(el), `sw=${el.scrollWidth} cw=${el.clientWidth}`);
    if (cs.overflowX === 'visible' && /^(BUTTON|TH|TD|SUMMARY|SELECT)$/.test(el.tagName) && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) add('SPILL ' + desc(el), `sw=${el.scrollWidth} cw=${el.clientWidth}`);
  }
  for (const m of document.querySelectorAll('.modal-overlay:not(.hidden)')) {
    const card = m.firstElementChild; if (!card) continue; const r = card.getBoundingClientRect();
    if (r.bottom > vh + 1 || r.top < -1 || r.right > vw + 1 || r.left < -1) add('MODAL-OUT ' + desc(card), `[${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.right)},${Math.round(r.bottom)}] vp=${vw}x${vh}`);
  }
  return issues.slice(0, 30);
};
const audits = {};
const S_ = async name => { await shot(page, `${out}/${name}.png`); try { const a = await page.evaluate(AUDIT); if (a.length) audits[name] = a; } catch (e) { audits[name] = ['audit error: ' + e.message.split('\n')[0]]; } };
const click = async sel => { try { await page.click(sel); await sleep(180); } catch (e) { fails.push(`${sel}: ${e.message.split('\n')[0]}`); } };
const scrollTo = async (id, top) => { await page.evaluate((id, top) => { const p = document.getElementById(id); if (p) p.scrollTop = top; }, id, top); await sleep(150); };
const scrollIntoView = async sel => { await page.evaluate(s => { const e = document.querySelector(s); if (e) e.scrollIntoView({ block: 'center' }); }, sel); await sleep(150); };
const closeModals = async () => { await page.evaluate(() => document.querySelectorAll('.modal-overlay').forEach(m => { if (!m.classList.contains('hidden')) toggleModal(m.id, false); })); await sleep(120); };
const step = async (name, fn) => { try { await fn(); } catch (e) { fails.push(`[${name}] ${e.message.split('\n')[0]}`); } };

await S_('a01_default');
await loadConfig(page, 'Vesna v3.1.6.json');
await S_('a02_char');
await step('quicksetter', async () => {
  await click('#toggleQuickSetter');
  await page.evaluate(() => document.querySelectorAll('#quickSetter details').forEach(d => { d.open = true; }));
  await S_('a03_quicksetter');
  await scrollIntoView('#quickSetter details[data-sec="sec3"]');
  await S_('a04_quicksetter2');
  await click('#toggleQuickSetter');
});
await step('select', async () => { await scrollTo('characterWorkspace', 0); await click('#editorContent .editor-head .studio-select-trigger'); await S_('a05_select_open'); await page.keyboard.press('Escape'); });
await step('dmgmenu', async () => { await scrollIntoView('#addDmgBtn'); await click('#addDmgBtn'); await S_('a06_dmg_menu'); await click('#addDmgN'); await scrollIntoView('#dmgList > :last-child'); await S_('a07_invalid_card'); await page.evaluate(() => document.querySelector('#dmgList > :last-child [data-dd]').click()); });
await step('talents', async () => { await scrollIntoView('#talentList > :first-child'); await S_('a08_talents'); await click('#addTalent'); await scrollIntoView('#talentList > :last-child'); await S_('a09_talent_invalid'); await page.evaluate(() => document.querySelector('#talentList > :last-child [data-td]').click()); });
await scrollTo('characterWorkspace', 0);
await click('#navTimeline'); await S_('b01_timeline');
await scrollTo('timelineWorkspace', 520); await S_('b02_timeline_editor');
await click('#navMonster'); await S_('b03_monster');
await click('#btnMore'); await S_('c01_more_menu');
await click('#btnSettings'); await S_('c02_settings');
await page.evaluate(() => { if (!document.getElementById('cfgDmgShareToggle').classList.contains('on')) document.getElementById('cfgDmgShareToggle').click(); });
await click('#btnSaveSettings');
await click('#btnFormula'); await sleep(300); await S_('c03_formula');
await page.evaluate(() => { const b = document.querySelector('#formulaModal .modal-body'); b.scrollTop = b.scrollHeight; }); await S_('c04_formula_end');
await closeModals();
await click('#btnShowDetails'); await S_('c05_details'); await closeModals();
await step('inspect', async () => { await click('#resList [data-inspect]'); await S_('c06_inspect'); await closeModals(); await page.evaluate(() => document.querySelectorAll('#resList [data-inspect]')[5]?.click()); await sleep(200); await S_('c07_inspect2'); await closeModals(); });
await step('share', async () => { await click('#btnShowDmgShare'); await S_('c08_dmgshare'); const sl = await page.$('#dmgSharePie .pie-slice'); if (sl) { const b = await sl.boundingBox(); await page.mouse.move(b.x + b.width * 0.8, b.y + b.height * 0.5); await sleep(200); } await S_('c09_dmgshare_hover'); await closeModals(); });
await click('#navCharacters');
await step('baselines', async () => { await click('#addBaseBtn'); await page.evaluate(() => { const i = document.querySelector('#editorContent [data-f="critRate"]'); i.value = '42.3'; i.dispatchEvent(new Event('input', { bubbles: true })); }); await click('#addBaseBtn'); await page.evaluate(() => { const i = document.querySelector('#editorContent [data-f="critDMG"]'); i.value = '263.5'; i.dispatchEvent(new Event('input', { bubbles: true })); }); await sleep(150); await S_('c10_baselines'); });
await step('weapon', async () => {
  await click('#toggleQuickSetter'); await page.evaluate(() => document.getElementById('qsPickWeapon').click()); await sleep(250); await S_('d01_weapon_empty');
  await click('#wAddToggle'); await page.type('#wNewName', '雾切之回光'); await click('#wAddTal'); await S_('d02_weapon_form');
  await click('#wNewConfirm'); await page.type('#wNewName', '天空之刃'); await click('#wNewConfirm'); await click('#wAddToggle'); await S_('d03_weapon_list'); await closeModals();
});
await step('artifact', async () => {
  await page.evaluate(() => document.getElementById('qsPickArtifact').click()); await sleep(250);
  await click('#aAddToggle'); await page.type('#aNewName', '绝缘之旗印'); await click('#aNewAddSet'); await S_('d04_artifact_form');
  await click('#aNewConfirm'); await click('#aAddToggle'); await S_('d05_artifact_list'); await closeModals(); await click('#toggleQuickSetter');
});
await step('quicktable', async () => {
  await click('#btnMore'); await click('#btnQuickTable'); await S_('e01_qt_mode');
  await click('#addBaseBtn'); await page.evaluate(() => { const i = document.querySelector('#editorContent [data-f="critRate"]'); i.value = '60'; i.dispatchEvent(new Event('input', { bubbles: true })); }); await click('#addBaseBtn'); await S_('e02_qt_schemes');
  await click('#qtFinishBtn'); for (let i = 0; i < 80 && await page.evaluate(() => qtRunning); i++) await sleep(100); await sleep(300); await S_('e03_qt_result');
  await click('#qtToggleDmgShareBtn'); await click('#qtPrune'); await S_('e04_qt_result_share'); await closeModals();
});
await step('history', async () => { await page.evaluate(() => window.dispatchEvent(new Event('beforeunload'))); await click('#navHistory'); await S_('f01_history'); await closeModals(); });
await step('no-timeline', async () => {
  await page.evaluate(() => { document.getElementById('btnSettings').click(); document.getElementById('cfgTimelineToggle').click(); document.getElementById('btnSaveSettings').click(); }); await sleep(250);
  await click('#navTimeline'); await S_('g01_timeline_disabled'); await click('#navCharacters'); await scrollIntoView('#dmgList > :first-child'); await S_('g02_char_no_timeline');
});
await step('empty', async () => { await page.evaluate(() => document.getElementById('btnReset').click()); await sleep(250); await S_('g03_empty'); });
console.log('step failures:', fails.length, fails);
for (const [k, v] of Object.entries(audits)) console.log('audit', k, JSON.stringify(v));
console.log('audit: shots with findings', Object.keys(audits).length);
console.log('errors:', page.__errors.filter(e => !/ERR_(FILE_NOT_FOUND|CONNECTION|NAME_NOT|INTERNET)/.test(e)).length, page.__errors.filter(e => !/ERR_(FILE_NOT_FOUND|CONNECTION|NAME_NOT|INTERNET)/.test(e)).slice(0, 5));
await browser.close();
