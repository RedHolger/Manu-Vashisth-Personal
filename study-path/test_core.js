const a=require('node:assert/strict'),m=require('./model.js');const d={version:1,topics:[{id:'a',title:'A',requires:[],done:false},{id:'b',title:'B',requires:['a'],done:false}]};
a.throws(()=>m.toggle(d,'b'));const x=m.toggle(m.toggle(d,'a'),'b');a.equal(x.topics[1].done,true);a.throws(()=>m.toggle(x,'a'));a.equal(d.topics[0].done,false);
a.throws(()=>m.validate({version:1,topics:[{id:'a',title:'A',requires:['a'],done:false}]}));a.throws(()=>m.validate({version:1,topics:[{id:'a',title:'A',requires:['missing'],done:false}]}));
a.throws(()=>m.validate({version:1,topics:[{id:'a',title:'A',requires:[],done:false},{id:'b',title:'B',requires:['a'],done:true}]}));
console.log('PASS: StudyPath model checks (7 assertions); browser study remains pending');
