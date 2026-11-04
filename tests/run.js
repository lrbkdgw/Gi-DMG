const fs=require('fs'),vm=require('vm');
const {El,makeDocument}=require('./dom.js');
const FILE=require('path').join(__dirname,'..','Gi DMG v2.2.0.html');
const html=fs.readFileSync(FILE,'utf8');
const i=html.indexOf('<script>\nconst $ = id'), j=html.indexOf('</script>',i);
const js=html.slice(i+9,j);
function boot(){
  const document=makeDocument();
  const ids=new Set(); const re=/id="([A-Za-z0-9_\-]+)"/g; let m;
  while((m=re.exec(html)))ids.add(m[1]);
  ids.forEach(id=>{const el=new El('div',document);el.id=id;document._byId.set(id,el);});
  const store={};
  const ctx={document,localStorage:{getItem:k=>(k in store?store[k]:null),setItem:(k,v)=>{store[k]=String(v);},removeItem:k=>{delete store[k];}},console,
    requestAnimationFrame:()=>0,setTimeout:()=>0,setInterval:()=>0,clearTimeout:()=>{},clearInterval:()=>{},
    alert:()=>{},confirm:()=>true,prompt:()=>null,navigator:{userAgent:'node'},location:{href:'file:///x',search:''},
    MutationObserver:class{observe(){}disconnect(){}},HTMLElement:El,
    Blob:class{},URL:{createObjectURL:()=>'blob:x',revokeObjectURL(){}},
    Event:class{constructor(t){this.type=t;}},CustomEvent:class{constructor(t,o){this.type=t;this.detail=o&&o.detail;}}};
  ctx.addEventListener=()=>{};ctx.removeEventListener=()=>{};ctx.dispatchEvent=()=>true;
  ctx.window=ctx;ctx.globalThis=ctx;
  vm.createContext(ctx);
  vm.runInContext(js,ctx,{filename:'gi-dmg-v220.js'});
  return ctx;
}
module.exports={boot,html,js,vm};
if(require.main===module){const c=boot();console.log('booted, timeline=',vm.runInContext('S.timeline.length',c));}
