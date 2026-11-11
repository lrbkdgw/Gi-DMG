// 真实鼠标/键盘交互与导入导出的对照检查：node qa/interact.mjs [new.html] [orig.html]
// 同一套操作分别在原版与新版上执行，结果必须一致；任何一项不一致则以非零状态退出。
import { launch, open, loadConfig, sleep, REPO } from './lib.mjs';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const NEW = process.argv[2] || path.join(REPO, 'Gi DMG v2.2.0.html');
const ORIG = process.argv[3] || '/tmp/gi-orig/full.html';
const TMP = '/tmp/qa_cfg'; fs.mkdirSync(TMP, { recursive: true });   // uploadFile 不支持非 ASCII 路径，统一用这里的 ASCII 文件名
const sha = s => crypto.createHash('sha256').update(s || '').digest('hex').slice(0, 16);
const CRIT = '#editorContent [data-f="critRate"]';
const browser = await launch();
let failed = 0;
const check = (name, ok, detail = '') => { console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + detail : '')); if (!ok) failed++; };

async function fresh(file) {
  const page = await open(browser, file, { seed: 5, quiet: true });
  page.__dialogs = [];
  page.on('dialog', async d => { page.__dialogs.push(d.type()); await d.accept(d.type() === 'prompt' ? (d.defaultValue() || '1') : undefined); });
  await loadConfig(page, 'Vesna v3.1.6.json');
  return page;
}
const critState = page => page.evaluate(() => S.chars.find(c => c.id === S.selId).critRate);
const total = page => page.evaluate(() => document.getElementById('totalDmg').textContent.trim());

// 1) 键盘输入：三击全选 / Ctrl+A / Tab 进入后直接键入，都应替换原值
async function typing(file) {
  const out = {};
  let p = await fresh(file); await p.click(CRIT, { count: 3 }); await p.keyboard.type('66.6'); await sleep(200); out.triple = [await critState(p), await total(p)]; await p.close();
  p = await fresh(file); await p.click(CRIT); await p.keyboard.down('Control'); await p.keyboard.press('KeyA'); await p.keyboard.up('Control'); await p.keyboard.type('61.5'); await sleep(200); out.ctrlA = [await critState(p), await total(p)]; await p.close();
  p = await fresh(file); await p.focus('#editorContent [data-f="em"]'); await p.keyboard.press('Tab'); await p.keyboard.type('44'); await sleep(200); out.tab = [await critState(p), await total(p)]; await p.close();
  p = await fresh(file); await p.click('#editorContent [data-f="name"]', { count: 3 }); await p.keyboard.type('abc'); await sleep(200); out.name = await p.evaluate(() => S.chars.find(c => c.id === S.selId).name); await p.close();
  return out;
}

// 2) 导出：系统保存对话框路径（用桩捕获写入内容）与普通下载回退路径
async function exportVia(file, mode) {
  const p = await fresh(file);
  await p.click(CRIT, { count: 3 }); await p.keyboard.type('61.5'); await sleep(200);
  if (mode === 'picker') await p.evaluate(() => { window.showSaveFilePicker = async o => { window.__opts = o; return { createWritable: async () => ({ write: async s => { window.__text = s; }, close: async () => { window.__closed = true; } }) }; }; });
  else await p.evaluate(() => { window.showSaveFilePicker = undefined; const c = URL.createObjectURL; URL.createObjectURL = b => { window.__blob = b; return c.call(URL, b); }; HTMLAnchorElement.prototype.click = function () { window.__name = this.download; }; });
  await p.click('#btnExport'); await sleep(400);
  const r = await p.evaluate(async m => m === 'picker' ? { text: window.__text || null, name: window.__opts && window.__opts.suggestedName, closed: !!window.__closed } : { text: window.__blob ? await window.__blob.text() : null, name: window.__name, type: window.__blob && window.__blob.type }, mode);
  r.dialogs = p.__dialogs.join(','); r.errors = p.__errors.filter(e => !/net::ERR_/.test(e)).length;
  await p.close();
  return r;
}

// 3) 导入：通过页面上真实的文件输入框
async function importInto(file, jsonPath) {
  const p = await open(browser, file, { seed: 9, quiet: true });
  p.on('dialog', async d => { await d.accept(); });
  await (await p.$('#importFile')).uploadFile(jsonPath); await sleep(600);
  const r = await p.evaluate(() => ({ chars: S.chars.length, state: JSON.stringify(S), total: document.getElementById('totalDmg').textContent.trim() }));
  await p.close();
  return { chars: r.chars, total: r.total, sha: sha(r.state) };
}

// 4) 拉表模式下各入口的显隐
async function qtVisibility(file) {
  const IDS = ['btnExport', 'btnImport', 'btnFormula', 'btnMore', 'navHistory', 'navTimeline', 'navMonster', 'addCharBtn', 'qtModeBanner', 'cfgBaseModeRow'];
  const p = await fresh(file);
  const vis = () => p.evaluate(ids => ids.map(id => { const el = document.getElementById(id); if (!el) return id + ':absent'; return id + ':' + (getComputedStyle(el).display === 'none' || el.getBoundingClientRect().width === 0 ? 'hidden' : 'shown'); }).join(' '), IDS);
  const normal = await vis();
  await p.evaluate(() => document.getElementById('btnQuickTable').click()); await sleep(300);
  const qt = await vis();
  await p.close();
  return { normal, qt };
}

const tn = await typing(NEW), to = await typing(ORIG);
check('三击全选后键入会替换原值', tn.triple[0] === 66.6 && JSON.stringify(tn.triple) === JSON.stringify(to.triple), JSON.stringify(tn.triple));
check('Ctrl+A 后键入会替换原值', tn.ctrlA[0] === 61.5 && JSON.stringify(tn.ctrlA) === JSON.stringify(to.ctrlA), JSON.stringify(tn.ctrlA));
check('Tab 进入输入框后键入会替换原值', tn.tab[0] === 44 && JSON.stringify(tn.tab) === JSON.stringify(to.tab), JSON.stringify(tn.tab));
check('文本框三击后键入', tn.name === 'abc' && to.name === 'abc');

for (const mode of ['picker', 'fallback']) {
  const n = await exportVia(NEW, mode), o = await exportVia(ORIG, mode);
  check(`导出（${mode === 'picker' ? '系统保存对话框' : '普通下载回退'}）内容与原版逐字节一致`, !!n.text && n.text === o.text && n.name === 'genshin-dmg.json' && n.name === o.name && n.dialogs === o.dialogs && n.errors === 0, `${n.text ? n.text.length : 0} 字符 sha=${sha(n.text)} name=${n.name} dialogs=[${n.dialogs}]`);
  if (mode === 'picker') { fs.writeFileSync(TMP + '/exp_new.json', n.text || ''); fs.writeFileSync(TMP + '/exp_orig.json', o.text || ''); }
}
const rt = { n2o: await importInto(ORIG, TMP + '/exp_new.json'), n2n: await importInto(NEW, TMP + '/exp_new.json'), o2n: await importInto(NEW, TMP + '/exp_orig.json'), o2o: await importInto(ORIG, TMP + '/exp_orig.json') };
const same = new Set(Object.values(rt).map(r => JSON.stringify(r)));
check('导出→导入往返：新版/原版四种组合得到相同状态与总伤害', same.size === 1 && rt.n2n.chars === 4, JSON.stringify(rt.n2n));

const vn = await qtVisibility(NEW), vo = await qtVisibility(ORIG);
check('常规模式下入口显隐与原版一致', vn.normal === vo.normal);
check('拉表模式下入口显隐与原版一致', vn.qt === vo.qt, vn.qt);

await browser.close();
console.log(failed ? `INTERACT FAILED (${failed})` : 'INTERACT OK');
process.exit(failed ? 1 : 0);
