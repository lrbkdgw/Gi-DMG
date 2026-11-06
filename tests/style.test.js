/* 样式完整性：成品里用到的每个 class 必须在两份内联样式表中有定义，
   否则元素会以“裸样式”呈现（v2.2.0 迁移新配色时就踩过这个坑）。 */
const fs=require('fs'),path=require('path');
const FILE=path.join(__dirname,'..','Gi DMG v2.2.0.html');
const html=fs.readFileSync(FILE,'utf8');

function sheet(id){
  const i=html.indexOf('<style id="'+id+'">');
  if(i<0)return '';
  return html.slice(i,html.indexOf('</style>',i));
}
const css=sheet('embedded-tailwind')+sheet('gi-dmg-design-system');
const esc=c=>c.replace(/([\[\]#%./:!])/g,'\\$1');
const hasClass=c=>css.includes('.'+esc(c));

function scan(src,label){
  const used=new Set();
  for(const m of src.matchAll(/class="([^"$`]*)/g)){
    for(const c of m[1].split(/\s+/)){
      if(/^[!A-Za-z][\w:./\[\]#%()-]*$/.test(c))used.add(c);
    }
  }
  return {label,total:used.size,missing:[...used].filter(c=>!hasClass(c)).sort()};
}

const bodyStart=html.indexOf('<body'),bodyEnd=html.indexOf('<script',bodyStart);
const jsStart=html.indexOf('<script>\nconst $ = id'),jsEnd=html.indexOf('</script>',jsStart);

let fail=0;
for(const r of [scan(html.slice(bodyStart,bodyEnd),'静态标记'),scan(html.slice(jsStart+9,jsEnd),'JS 模板')]){
  if(r.missing.length){
    fail++;
    console.log(`  ✗ ${r.label}: ${r.total} 个类中 ${r.missing.length} 个无样式`);
    console.log('    '+r.missing.join(' '));
  }else{
    console.log(`  ✓ ${r.label}: ${r.total} 个类全部有样式`);
  }
}

/* 标签结构配对 */
const count=(re)=> (html.match(re)||[]).length;
const pairs=[
  ['style', /<style\b/g, /<\/style>/g],
  ['script', /<script\b/g, /<\/script>/g],
  ['div', /<div\b/g, /<\/div>/g],
  ['html', /<html\b/g, /<\/html>/g],
  ['head', /<head\b/g, /<\/head>/g],
];
for(const [name,open,close] of pairs){
  const a=count(open), b=count(close);
  if(a!==b){fail++;console.log(`  ✗ <${name}> 开合数量不等 (${a} / ${b})`);}
  else console.log(`  ✓ <${name}> 配对 (${a})`);
}

console.log(fail?`\n结果: ${fail} 项失败`:'\n结果: 全部通过');
process.exit(fail?1:0);
