// 整页切片（单列布局用）：node qa/slices.mjs <html> <outdir> <W> <H> <char|timeline|monster> <sliceH> [dark]   环境变量 CFG / MAXN
import { launch, open, loadConfig, sleep } from './lib.mjs';
import fs from 'node:fs';
const [file, out, W, H, nav, sliceH, theme] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const browser = await launch();
const page = await open(browser, file, { seed: 42, theme: theme === 'dark' ? 'dark' : null, quiet: true, width: +W, height: +H });
await loadConfig(page, process.env.CFG || 'Vesna v3.1.6.json');
if (nav === 'timeline') await page.click('#navTimeline');
if (nav === 'monster') await page.click('#navMonster');
await sleep(400);
const sh = await page.evaluate(() => document.documentElement.scrollHeight);
console.log('scrollHeight', sh);
const n = Math.min(Math.ceil(sh / +sliceH), +(process.env.MAXN || 6));
for (let i = 0; i < n; i++) {
  const h = Math.min(+sliceH, sh - i * +sliceH);
  await page.screenshot({ path: `${out}/s_${nav}_${i}.png`, clip: { x: 0, y: i * +sliceH, width: +W, height: h } });
}
console.log('errors', page.__errors.filter(e => !/net::ERR_/.test(e)).length);
await browser.close();
