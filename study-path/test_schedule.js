'use strict';
// P14-02: conflicts visible, imports preserve state, prerequisites consistent.
const a = require('node:assert/strict');
const s = require('./schedule.js');
const model = require('./model.js');

const plan = () => ({ version: 1, topics: [
  { id: 'a', title: 'A', requires: [], done: false },
  { id: 'b', title: 'B', requires: ['a'], done: false }] });

a.deepEqual(s.detectConflicts([
  { id: 'x', day: 'Thu', startMin: 60, endMin: 120 },
  { id: 'y', day: 'Thu', startMin: 90, endMin: 150 }]),
  [{ a: 'x', b: 'y', day: 'Thu' }]);
a.deepEqual(s.detectConflicts([
  { id: 'x', day: 'Thu', startMin: 60, endMin: 120 },
  { id: 'y', day: 'Fri', startMin: 90, endMin: 150 }]), []);
const added = s.planBlock([], { id: 'n', day: 'Thu', startMin: 0, endMin: 90 });
a.equal(added.blocks.length, 1);
a.equal(added.conflict, null);
const clash = s.planBlock([{ id: 'e', day: 'Thu', startMin: 0, endMin: 90 }],
  { id: 'n', day: 'Thu', startMin: 30, endMin: 60 });
a.deepEqual(clash.conflict, ['e']);
a.equal(clash.blocks.length, 1);
a.throws(() => s.planBlock([], { id: 'n', day: 'Thu', startMin: 5, endMin: 5 }));

const cur = plan();
const badCycle = JSON.stringify({ version: 1, topics: [{ id: 'a', title: 'A', requires: ['a'], done: false }] });
const kept = s.importPlan(cur, badCycle);
a.equal(kept.plan, cur);
a.ok(kept.error);
const kept2 = s.importPlan(cur, 'not json');
a.equal(kept2.plan, cur);
const inconsistent = JSON.stringify({ version: 1, topics: [
  { id: 'a', title: 'A', requires: [], done: false },
  { id: 'b', title: 'B', requires: ['a'], done: true }] });
const kept3 = s.importPlan(cur, inconsistent);
a.equal(kept3.plan, cur);
const ok = s.importPlan(cur, JSON.stringify(plan()));
a.equal(ok.error, null);
a.equal(s.exportPlan(plan()), JSON.stringify(model.validate(plan()), null, 2));
a.equal(s.progressConsistency(plan()), true);
console.log('PASS: P14-02 scheduling checks (conflicts, import preservation, consistency); browser study pending');
