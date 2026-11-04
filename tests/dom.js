function makeClassList(el){
  const set=new Set();
  return {add:(...c)=>c.forEach(x=>x&&set.add(x)),remove:(...c)=>c.forEach(x=>set.delete(x)),
    contains:c=>set.has(c),toggle:(c,f)=>{const on=f===undefined?!set.has(c):!!f;on?set.add(c):set.delete(c);return on;},_set:set};
}
class El {
  constructor(tag,doc){this.tagName=(tag||'div').toUpperCase();this.ownerDocument=doc;this.children=[];this.dataset={};
    this.style={setProperty(){}};this._attrs={};this.value='';this.type='';this.options=[];this.selectedIndex=0;
    this.checked=false;this.textContent='';this._html='';this.parentNode=null;this.isConnected=true;this._cl=makeClassList(this);}
  get classList(){return this._cl||(this._cl=makeClassList(this));}
  set className(v){this._cls=v;this._cl=makeClassList(this);String(v||'').split(/\s+/).filter(Boolean).forEach(c=>this._cl._set.add(c));}
  get className(){return this._cl?[...this._cl._set].join(' '):(this._cls||'');}
  get innerHTML(){return this._html;}
  set innerHTML(v){this._html=String(v);}
  appendChild(c){this.children.push(c);if(c)c.parentNode=this;return c;}
  append(...cs){cs.forEach(c=>this.appendChild(c));}
  insertBefore(c){this.children.push(c);c.parentNode=this;return c;}
  removeChild(c){this.children=this.children.filter(x=>x!==c);return c;}
  remove(){if(this.parentNode)this.parentNode.removeChild(this);}
  setAttribute(k,v){this._attrs[k]=String(v);}
  getAttribute(k){return this._attrs[k];}
  removeAttribute(k){delete this._attrs[k];}
  addEventListener(){} removeEventListener(){} dispatchEvent(){return true;}
  querySelector(sel){ if(!this._qsCache)this._qsCache=new Map(); if(this._qsCache.has(sel))return this._qsCache.get(sel);
    const el=new El('div',this.ownerDocument); el.id=String(sel).replace(/[^A-Za-z0-9_-]/g,''); this._qsCache.set(sel,el); return el; }
  querySelectorAll(){return [];}
  closest(){return null;} matches(){return false;} contains(){return false;}
  focus(){} blur(){} scrollIntoView(){} replaceChildren(){this.children=[];}
  getBoundingClientRect(){return {top:0,left:0,width:100,height:20};}
  set onclick(f){this._onclick=f;} get onclick(){return this._onclick;}
}
function makeDocument(){
  const doc={_byId:new Map(),readyState:'complete',activeElement:null,
    createElement(t){return new El(t,doc);},createElementNS(ns,t){return new El(t,doc);},
    createTextNode(t){return {nodeType:3,textContent:String(t)};},
    getElementById(id){return doc._byId.get(id)||null;},
    querySelector(sel){return doc.body.querySelector(sel);},querySelectorAll(){return [];},
    addEventListener(){},removeEventListener(){},dispatchEvent(){return true;}};
  doc.body=new El('body',doc); doc.documentElement=new El('html',doc); doc.body.parentElement=doc.documentElement;
  return doc;
}
module.exports={El,makeDocument};
