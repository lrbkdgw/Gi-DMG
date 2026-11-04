const fs=require('fs'),path=require('path'),vm=require('vm');
const {boot}=require('./run.js');
const DIR=require('path').join(__dirname,'..','finish_date');
let pass=0,fail=0;
const ok=(n,c,x)=>{if(c){pass++;console.log('  ✓',n);}else{fail++;console.log('  ✗',n,x!==undefined?'→ '+x:'');}};
const c=boot(); const run=k=>vm.runInContext(k,c);
const load=f=>{c.__raw=JSON.parse(fs.readFileSync(path.join(DIR,f),'utf8'));run('S=normalizeState(__raw);tlInvalidate();calc();');};

console.log('\n=== A. 静态模式 = v2.1.9，时间轴模式 = 迁移后真值 ===');
const stRef={'Mitya v3.2.1.json':2694209,'Vesna v3.1.6.json':3812919,'月绽放 2.json':0,'温迪 2.json':3165703,'火神.json':5015567};
const tlRef={'Mitya v3.2.1.json':2651587,'Vesna v3.1.6.json':3853089,'月绽放 2.json':0,'温迪 2.json':3165703,'火神.json':5015567};
for(const f of fs.readdirSync(DIR).filter(x=>x.endsWith('.json'))){
  load(f);
  const tl=run('window.__lastCalc.total'),dps=run('window.__lastCalc.dps'),rot=run('tlRot()');
  run('S.timelineEnabled=false;calc();');const st=run('window.__lastCalc.total');
  ok(f+' 静态 = v2.1.9',Math.abs(st-stRef[f])<1,Math.round(st));
  ok(f+' 时间轴 = 预期',Math.abs(tl-tlRef[f])<1,Math.round(tl));
  ok(f+' DPS = 总伤/轴长',Math.abs(dps-tl/rot)<1e-6);
  const inv=run(`(function(){const bad=[],dang=[],dup=[],miss=[];const ids=new Set();
    S.chars.forEach(c=>{(c.dmgSrcs||[]).forEach(d=>['startTime','duration','timingMode'].forEach(k=>{if(k in d)bad.push(k);}));
      (c.talents||[]).forEach(t=>['startTime','duration','isPermanent'].forEach(k=>{if(k in t)bad.push(k);}));
      (((c.qs||{}).weapon||{}).talents||[]).forEach(t=>['startTime','duration'].forEach(k=>{if(k in t)bad.push(k);}));
      (((c.qs||{}).artifact||{}).sets||[]).forEach(t=>['startTime','duration'].forEach(k=>{if(k in t)bad.push(k);}));
      (c.dmgSrcs||[]).forEach(d=>{if(!tlEventsUsing('dmg:'+d.id).length)miss.push(d.name);});});
    S.timeline.forEach(e=>{if(ids.has(e.id))dup.push(e.id);ids.add(e.id);if(!tlRefTarget(e.refId))dang.push(e.refId);});
    return {bad,dang,dup,miss};})()`);
  ok(f+' 迁移不变量',inv.bad.length===0&&inv.dang.length===0&&inv.dup.length===0&&inv.miss.length===0,
     (inv.bad[0]||inv.dang[0]||inv.dup[0]||inv.miss[0]||''));
}

console.log('\n=== B. 解析积分 ===');
run(`const mk=(id)=>{const x=defChar('pyro');x.id=id;x.name=id;x.baseAtk=1000;x.weaponAtk=0;x.atkPct=0;x.atkFlat=0;x.critRate=100;x.critDMG=100;x.em=0;x.dmgSrcs=[];x.talents=[];return x;};
const A=mk('A'),B=mk('B');
A.dmgSrcs=[{id:'d1',on:true,type:'normal',name:'斩',stat:'atk',mult:100,element:'pyro',dmgType:'NA',reaction:'none',triggerCharId:'A',statCharId:'A',contribs:[]}];
B.talents=[{id:'t1',on:true,source:'manual',name:'buff',effs:[{cat:'stat',type:'atk_pct',target:'team',value:100}]}];
S={timelineEnabled:true,dmgShareEnabled:false,rotationDuration:20,enemy:{level:93,res:{}},chars:[A,B],selId:'A',baselines:[],timeline:[]};
window.T=tail=>{S.timeline=[{id:'e1',kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'duration',startTime:0,endTime:20,lockPanel:false}].concat(tail);tlInvalidate();calc();return window.__lastCalc.total;};`);
const full=run(`T([{id:'e2',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:0,endTime:20}])`),
      none=run(`T([])`),
      half=run(`T([{id:'e2',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:0,endTime:10}])`),
      q=run(`T([{id:'e2',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:5,endTime:12.5}])`),
      wrap=run(`T([{id:'e2',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:15,endTime:25}])`);
const bump=x=>(x-none)/(full-none);
ok('[0,10] 权重 = 0.5',Math.abs(bump(half)-0.5)<1e-9,bump(half));
ok('[5,12.5] 权重 = 0.375',Math.abs(bump(q)-0.375)<1e-6,bump(q));
ok('[15,25] 跨轴 = 0.5',Math.abs(bump(wrap)-0.5)<1e-6,bump(wrap));
ok('跨轴拆两段',JSON.stringify(run(`tlIntervalsOfEvent({refId:'manual:t1',timingMode:'duration',startTime:15,endTime:25})`))==='[[15,20],[0,5]]');

console.log('\n=== C. 事件列表与锁面板 ===');
run(`window.T2=n=>{S.timeline=[];for(let i=0;i<n;i++)S.timeline.push({id:'x'+i,kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'instant',startTime:i*6,endTime:i*6});tlInvalidate();calc();return window.__lastCalc.total;};`);
ok('同源 3 次 = 3×',Math.abs(run('T2(3)')-3*run('T2(1)'))<1e-6);
const snap=run(`(function(){S.timeline=[{id:'a',kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'duration',startTime:0,endTime:20,lockPanel:true},{id:'b',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:10,endTime:20}];tlInvalidate();calc();return window.__lastCalc.total;})()`);
const dyn=run(`(function(){S.timeline[0].lockPanel=false;tlInvalidate();calc();return window.__lastCalc.total;})()`);
ok('锁面板 < 随动',snap<dyn,snap+' vs '+dyn);
ok('随动权重 = 0.5',Math.abs((dyn-none)/(full-none)-0.5)<1e-6);

console.log('\n=== D. 排序 / 标签 / 剪枝 / 补充 ===');
ok('排序',JSON.stringify(run(`(function(){S.timeline=[{id:'z',kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'instant',startTime:5},{id:'a',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:5,endTime:9},{id:'m',kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'instant',startTime:1}];tlSortEvents();return S.timeline.map(e=>e.id);})()`))==='["m","a","z"]');
ok('标签',JSON.stringify(run(`(function(){S.timeline=[{id:'a',kind:'talent',charId:'B',refId:'manual:t1',timingMode:'duration',startTime:5,endTime:9}];const d=tlScheduleLabel('manual:t1');S.timeline[0].timingMode='permanent';const p=tlScheduleLabel('manual:t1');S.timeline=[{id:'b',kind:'dmg',charId:'A',refId:'dmg:d1',timingMode:'instant',startTime:3}];return [d,p,tlScheduleLabel('dmg:d1'),tlScheduleLabel('manual:none')];})()`))==='["5s ~ 9s","全程覆盖","3s 瞬发",null]');
ok('剪枝',run(`(function(){S.timeline=[{id:'a',kind:'dmg',charId:'A',refId:'dmg:gone',timingMode:'instant',startTime:0}];tlPruneEvents();return S.timeline.length;})()`)===0);
const sy=run(`(function(){S.timeline=[];const n=tlUnscheduledCount(),a=tlSyncUnscheduled();return [n,a,S.timeline.length,tlUnscheduledCount()];})()`);
ok('一键补充',sy[0]===sy[1]&&sy[0]===sy[2]&&sy[3]===0,JSON.stringify(sy));

console.log('\n=== E. 全链路渲染冒烟 ===');
for(const f of fs.readdirSync(DIR).filter(x=>x.endsWith('.json'))){
  load(f);
  const errs=[];
  const safe=(l,code)=>{try{run(code);}catch(e){errs.push(l+': '+e.message);}};
  safe('renderAll','renderAll();');
  safe('时间轴','setWorkspace("timeline");renderTimelineCharFilters();renderTimelineEditorList();renderTimelineGraph();');
  safe('怪物','setWorkspace("monster");renderAll();');
  safe('角色','setWorkspace("character");renderAll();');
  safe('技能解析',`showSkillInspectModal(window.__lastCalc.results[0]&&window.__lastCalc.results[0].sourceId);`);
  safe('跳转',`jumpToSkill(S.chars[0].id,window.__lastCalc.results[0]&&window.__lastCalc.results[0].sourceId);`);
  safe('快照','makeConfigSnapshot();');
  safe('拉表','renderQuickTable();');
  safe('占比',`renderDmgShareSvg(window.__lastCalc.results.map((r,i)=>({name:r.dName,pct:100/window.__lastCalc.results.length,dmg:r.expected,color:'#155eef'})),window.__lastCalc.total);`);
  safe('方案','renderSchemeList();');
  safe('基础区','renderBaseSection();');
  safe('chip刷新','tlRefreshChips();');
  safe('技能面板区间',`(function(){const lc=window.__lastCalc;const k=Object.keys(lc.inspectMap)[0];const it=lc.inspectMap[k];if(it)getSkillPanelIntervals(it.d,it.owner,lc.en,it.ev||null);})();`);
  ok(f+' 无异常',errs.length===0,errs.slice(0,2).join(' | '));
}

console.log('\n=== F. 保存/载入往返 ===');
load('Vesna v3.1.6.json');
const rt=run(`(function(){const s=JSON.parse(JSON.stringify(makeConfigSnapshot()));const b={t:window.__lastCalc.total,n:S.timeline.length};S=normalizeState(s);tlInvalidate();calc();window.__rt={b,a:{t:window.__lastCalc.total,n:S.timeline.length},has:Array.isArray(s.timeline)};return 1;})()`);
const RT=JSON.parse(run('JSON.stringify(window.__rt)'));

ok('含 timeline',RT.has===true);
ok('总伤一致',Math.abs(RT.b.t-RT.a.t)<1e-6,RT.b.t+' vs '+RT.a.t+' Δ='+(RT.b.t-RT.a.t));
ok('节点数一致',RT.b.n===RT.a.n,RT.b.n+' vs '+RT.a.n);

console.log('\n'+'-'.repeat(40));
console.log(`结果: ${pass} 通过, ${fail} 失败`);
process.exit(fail?1:0);
