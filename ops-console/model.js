(function(root){
'use strict';
function validate(rows){
 if(!Array.isArray(rows)) throw new Error('Expected an incident array');
 const ids=new Set();
 return rows.map(r=>{
  if(!r || typeof r.id!=='string' || !r.id || ids.has(r.id)) throw new Error('Invalid or duplicate ID');
  ids.add(r.id);
  if(!['OPEN','VERIFYING','RESOLVED','UNKNOWN'].includes(r.state)) throw new Error('Invalid state');
  if(typeof r.service!=='string' || !Array.isArray(r.events)) throw new Error('Invalid incident');
  if(!Number.isFinite(Date.parse(r.updated))) throw new Error('Invalid date');
  if(r.events.some(e=>!e || typeof e.text!=='string'||!Number.isFinite(Date.parse(e.at))))throw new Error('Invalid event');
  return {...r,events:[...r.events].sort((a,b)=>Date.parse(a.at)-Date.parse(b.at))};
 });
}
function select(rows,query='',state='ALL'){
 return rows.filter(r=>(state==='ALL'||r.state===state)&&(r.id+' '+r.service).toLowerCase().includes(query.toLowerCase()));
}
function freshness(row,now,limit=60000){return now-Date.parse(row.updated)>limit?'STALE':now<Date.parse(row.updated)?'CLOCK_SKEW':'CURRENT';}
const api={validate,select,freshness};if(typeof module!=='undefined')module.exports=api;else root.OpsModel=api;
})(globalThis);
