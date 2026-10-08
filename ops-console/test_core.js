const a=require('node:assert/strict'),m=require('./model.js');
const r={id:'1',service:'api',state:'OPEN',updated:'2026-01-01T00:00:00Z',events:[]};
a.equal(m.validate([r]).length,1);a.throws(()=>m.validate([r,r]));a.throws(()=>m.validate([{...r,state:'FAKE'}]));
a.equal(m.select([r],'api').length,1);a.equal(m.select([r],'missing').length,0);
a.equal(m.freshness(r,Date.parse(r.updated)+60001),'STALE');a.equal(m.freshness(r,0),'CLOCK_SKEW');
console.log('PASS: OpsConsole model checks (7 assertions); browser/a11y review remains pending');
