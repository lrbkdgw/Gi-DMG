import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire('/tmp/tools/');
const chromium = require('@sparticuz/chromium').default || require('@sparticuz/chromium');
const puppeteer = require('puppeteer-core');
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO = path.resolve(ROOT, '..');
export const CFG_DIR = path.join(REPO, 'finish_date') + '/';
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export async function launch() {
  const executablePath = await chromium.executablePath();
  return puppeteer.launch({ args: [...chromium.args, '--force-color-profile=srgb'], executablePath, headless: 'shell', defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 1 } });
}
export async function open(browser, file, { width = 1440, height = 900, seed = null, theme = null, quiet = false, dpr = 1 } = {}) {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') { errors.push(m.text()); if (!quiet) console.log('[console.error]', m.text().slice(0, 300)); } });
  page.on('pageerror', e => { errors.push('PAGEERROR ' + String(e.message)); console.log('[pageerror]', String(e.message).slice(0, 500)); });
  await page.setViewport({ width, height, deviceScaleFactor: dpr });
  if (seed !== null) {
    await page.evaluateOnNewDocument((s) => {
      let a = s >>> 0;
      Math.random = function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    }, seed);
  }
  if (theme) await page.evaluateOnNewDocument((t) => { try { localStorage.setItem('gs_theme', t); } catch (e) {} }, theme);
  await page.goto('file://' + encodeURI(path.resolve(file)), { waitUntil: 'load', timeout: 60000 });
  await sleep(400);
  page.__errors = errors;
  return page;
}
export async function loadConfig(page, name) {
  const json = fs.readFileSync(CFG_DIR + name, 'utf8');
  await page.evaluate((j) => { S = normalizeState(JSON.parse(j)); rERes(); $('enemyLevel').value = S.enemy.level; S.baselines = S.baselines || []; renderAll(); }, json);
  await sleep(350);
}
export async function shot(page, file, opts = {}) { await sleep(opts.wait ?? 250); await page.screenshot({ path: file, ...(opts.clip ? { clip: opts.clip } : {}), fullPage: !!opts.fullPage }); }
