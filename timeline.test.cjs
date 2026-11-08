// Run with: node --test timeline.test.cjs (Node.js 18+; no dependencies).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'Gi DMG v2.2.0.html'),'utf8');
const script=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).find(s=>s.includes('function calc()'));
assert.ok(script,'Application script is present');
new vm.Script(script); // Check the complete application, including UI bindings.
const boundary=script.indexOf("$('closeSkillPanelModal').onclick");
assert.ok(boundary>0,'Headless core boundary is present');
const snapshot=script.slice(script.indexOf('function makeConfigSnapshot()'),script.indexOf('function restoreBaselineConfig('));
function engine(){
  const context=vm.createContext({window:{},document:{getElementById:()=>null,addEventListener:()=>{}},localStorage:{getItem:()=>null}});
  // Load the actual calculator and its constants. Only DOM event binding is omitted.
  vm.runInContext(script.slice(0,boundary)+'\n'+snapshot+'\nsuppressCalcUI=true;',context);
  return code=>vm.runInContext(code,context);
}
const fixture="var c=defChar();c.id='char';c.dmgSrcs=[{id:'source',on:true,type:'normal',name:'Hit',stat:'atk',mult:100,element:'pyro',dmgType:'E',reaction:'none'}];S.chars=[c];S.selId=c.id;";
const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<=1e-8*Math.max(1,Math.abs(expected)),actual+' != '+expected);

test('old source timing migrates once, preserving disabled entries',()=>{
 const run=engine();run(fixture+"c.dmgSrcs[0].on=false;c.dmgSrcs[0].timingMode='uniform_snapshot';c.dmgSrcs[0].startTime=2;c.dmgSrcs[0].duration=9;ensureTimelineQueue(c);var id=c.timelineQueue[0].id;ensureTimelineQueue(c);");
 assert.equal(run('c.timelineQueue.length'),1);assert.equal(run('c.timelineQueue[0].id===id'),true);
 assert.equal(run('c.timelineQueue[0].on'),false);assert.equal(run('c.timelineQueue[0].startTime'),2);assert.equal(run('c.timelineQueue[0].duration'),9);
});
test('repeated source occurrences double timeline damage with distinct inspections',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;var q=c.timelineQueue;q.push({...q[0],id:'second',startTime:5});calc();");
 near(run('window.__lastCalc.total'),run('base*2'));assert.equal(run('window.__lastCalc.results.length'),2);
 assert.equal(run('Object.keys(window.__lastCalc.inspectMap).length'),2);
 assert.equal(run('window.__lastCalc.results.every(r=>r.sourceId===\'source\')'),true);
});
test('static mode still calculates the source once',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;c.timelineQueue.push({...c.timelineQueue[0],id:'second'});S.timelineEnabled=false;calc();");
 near(run('window.__lastCalc.total'),run('base'));assert.equal(run('window.__lastCalc.results.length'),1);
});
test('each occurrence samples buffs at its own start time',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;c.talents=[{on:true,name:'ATK',startTime:1,duration:1,effs:[{cat:'stat',type:'atk_pct',target:'self',value:100}]}];c.timelineQueue[0].startTime=1.5;c.timelineQueue.push({...c.timelineQueue[0],id:'second',startTime:4});calc();");
 near(run('window.__lastCalc.results[0].expected'),run('base*2'));near(run('window.__lastCalc.results[1].expected'),run('base'));
});
test('source definition edits propagate to all scheduled occurrences',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;c.timelineQueue.push({...c.timelineQueue[0],id:'second'});c.dmgSrcs[0].mult=200;c.dmgSrcs[0].name='Updated';calc();");
 near(run('window.__lastCalc.total'),run('base*4'));assert.equal(run("window.__lastCalc.results.every(r=>r.dName==='Updated')"),true);
});
test('source-target effects apply to every occurrence, retaining definition IDs',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;c.timelineQueue.push({...c.timelineQueue[0],id:'second'});c.talents=[{on:true,always:true,name:'Source bonus',effs:[{cat:'dmgType',type:'all',target:'source:source',value:100}]}];calc();");
 near(run('window.__lastCalc.total'),run('base*4'));
});
test('individual and source switches exclude only their intended occurrences',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;c.timelineQueue.push({...c.timelineQueue[0],id:'second',on:false});calc();");
 near(run('window.__lastCalc.total'),run('base'));run('c.dmgSrcs[0].on=false;calc();');assert.equal(run('window.__lastCalc.total'),0);
});
test('an explicit empty queue remains empty through calculation and import',()=>{
 const run=engine();run(fixture+'c.timelineQueue=[];calc();S=normalizeState(JSON.parse(JSON.stringify(S)));calc();');
 assert.equal(run('S.chars[0].timelineQueue.length'),0);assert.equal(run('window.__lastCalc.total'),0);
});
test('deleting a source prunes its occurrences',()=>{
 const run=engine();run(fixture+"calc();c.timelineQueue.push({...c.timelineQueue[0],id:'second'});c.dmgSrcs=[];calc();");
 assert.equal(run('c.timelineQueue.length'),0);assert.equal(run('window.__lastCalc.results.length'),0);
});
test('duplicate imported event IDs are repaired and stale references removed',()=>{
 const run=engine();run(fixture+"c.timelineQueue=[{id:'same',sourceId:'source'},{id:'same',sourceId:'source'},{id:'stale',sourceId:'missing'}];ensureTimelineQueue(c);");
 assert.equal(run('c.timelineQueue.length'),2);assert.equal(run('new Set(c.timelineQueue.map(e=>e.id)).size'),2);
});
test('same event IDs on different characters have independent inspectors',()=>{
 const run=engine();run(fixture+"ensureTimelineQueue(c);c.timelineQueue[0].id='shared';var c2=JSON.parse(JSON.stringify(c));c2.id='other';c2.dmgSrcs[0].id='source2';c2.timelineQueue[0].sourceId='source2';S.chars.push(c2);calc();");
 assert.equal(run('Object.keys(window.__lastCalc.inspectMap).length'),2);assert.equal(run('new Set(window.__lastCalc.results.map(r=>r.inspectId)).size'),2);
});
test('narrow buff windows use exact integration instead of fixed sample counts',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;Object.assign(c.timelineQueue[0],{timingMode:'uniform_dynamic',startTime:0,duration:10});c.talents=[{on:true,name:'Short buff',startTime:0.02,duration:0.1,effs:[{cat:'stat',type:'atk_pct',target:'self',value:100}]}];calc();");
 near(run('window.__lastCalc.total'),run('base*1.01'));
});
test('snapshot locks panel stats while dynamic mode follows buff windows',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;Object.assign(c.timelineQueue[0],{timingMode:'uniform_snapshot',startTime:1,duration:4});c.talents=[{on:true,name:'Buff',startTime:1,duration:1,effs:[{cat:'stat',type:'atk_pct',target:'self',value:100}]}];calc();var snapshotDamage=window.__lastCalc.total;c.timelineQueue[0].timingMode='uniform_dynamic';calc();");
 near(run('snapshotDamage'),run('base*2'));near(run('window.__lastCalc.total'),run('base*1.25'));
});
test('buff integration crosses the rotation boundary',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;Object.assign(c.timelineQueue[0],{timingMode:'uniform_dynamic',startTime:18,duration:4});c.talents=[{on:true,name:'Wrap',startTime:19.5,duration:1,effs:[{cat:'stat',type:'atk_pct',target:'self',value:100}]}];calc();");
 near(run('window.__lastCalc.total'),run('base*1.25'));
});
test('multi-rotation durations retain the total multiplier',()=>{
 const run=engine();run(fixture+"calc();var base=window.__lastCalc.total;Object.assign(c.timelineQueue[0],{timingMode:'uniform_dynamic',startTime:0,duration:40});c.talents=[{on:true,name:'Buff',startTime:0,duration:2,effs:[{cat:'stat',type:'atk_pct',target:'self',value:100}]}];calc();");
 near(run('window.__lastCalc.total'),run('base*1.1'));
});
test('whole-rotation legacy talents become always-on for all talent types',()=>{
 const run=engine();run(fixture+"c.talents=[{on:true,startTime:0,duration:20,effs:[]}];c.qs.weapon.talents=[{on:true,startTime:0,duration:20,effs:[]}];c.qs.artifact.sets=[{on:true,startTime:0,duration:20,effs:[]}];S=normalizeState(S);");
 assert.equal(run('c.talents[0].always&&c.qs.weapon.talents[0].always&&c.qs.artifact.sets[0].always'),true);
});
test('config and baseline snapshots preserve independent timings and switches',()=>{
 const run=engine();run(fixture+"calc();c.timelineQueue.push({...c.timelineQueue[0],id:'second',startTime:8,on:false});var saved=makeConfigSnapshot();var before=JSON.stringify(saved.chars[0].timelineQueue);S=normalizeState(JSON.parse(JSON.stringify(saved)));");
 assert.equal(run('JSON.stringify(S.chars[0].timelineQueue)===before'),true);assert.equal(run('saved.chars[0]!==c'),true);
});
test('invalid entry times normalize to finite nonnegative values',()=>{
 const run=engine();run(fixture+"c.timelineQueue=[{id:'bad',sourceId:'source',startTime:Infinity,duration:-3,timingMode:'invalid'}];ensureTimelineQueue(c);");
 assert.equal(run('c.timelineQueue[0].startTime'),0);assert.equal(run('c.timelineQueue[0].duration'),0);assert.equal(run('c.timelineQueue[0].timingMode'),'instant');
});
