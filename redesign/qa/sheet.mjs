// 把多张截图拼成一张联系表，便于快速目检：node qa/sheet.mjs <out.png> <cols> <scale> <img...>
import { launch } from './lib.mjs';
import path from 'node:path';
import fs from 'node:fs';
const [out, cols, scale, ...imgs] = process.argv.slice(2);
const browser = await launch();
const page = await browser.newPage();
const html = `<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#888;font:12px monospace}.g{display:grid;grid-template-columns:repeat(${+cols},max-content);gap:6px;padding:6px}figure{margin:0;background:#222}figcaption{color:#fff;padding:2px 6px}img{display:block;zoom:${+scale}}</style><div class="g">${imgs.map(f => `<figure><figcaption>${path.basename(f, '.png')}</figcaption><img src="file://${path.resolve(f)}"></figure>`).join('')}</div>`;
// about:blank 不能加载 file:// 图片，所以先落盘再打开
const tmp = out.replace(/\.png$/, '') + '.sheet.html';
fs.writeFileSync(tmp, html);
await page.goto('file://' + path.resolve(tmp), { waitUntil: 'load' });
await page.evaluate(() => Promise.all([...document.images].map(i => i.decode().catch(() => {}))));
const size = await page.evaluate(() => { const g = document.querySelector('.g'); return { w: Math.ceil(g.getBoundingClientRect().width), h: Math.ceil(g.getBoundingClientRect().height) }; });
await page.setViewport({ width: size.w, height: size.h, deviceScaleFactor: 1 });
await page.screenshot({ path: out });
fs.unlinkSync(tmp);
console.log(out, size.w + 'x' + size.h, imgs.length);
await browser.close();
