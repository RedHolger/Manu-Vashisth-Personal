'use strict';
// P13-01: real exports adapt with provenance; missing stays UNKNOWN.
const a = require('node:assert/strict');
const model = require('./model.js');
const adapter = require('./adapter.js');

const rows = adapter.adaptVerificationRun(
  require('./testdata/real-metrics.json'),
  'ops-console/testdata/real-metrics.json');
a.ok(rows.length > 0);
a.ok(rows.every(r => r.state === 'UNKNOWN'));
a.ok(rows.every(r => r.provenance && r.provenance.sha256.length === 64));
a.ok(rows.every(r => r.provenance.kind === 'verification-run'));
a.equal(model.validate(rows).length, rows.length);
a.ok(!rows.some(r => r.state === 'RESOLVED'));
const syn = adapter.adaptSynthetic();
a.equal(syn[0].provenance.kind, 'synthetic');
a.equal(model.validate(syn).length, 1);
a.throws(() => adapter.adaptVerificationRun({}, 'ops-console/nope.json'));
a.equal(adapter.pendingGate().status, 'BLOCKED');
console.log(`PASS: P13-01 adapter checks (${rows.length} real rows UNKNOWN, synthetic labeled, missing refused); live SRE exports pending`);
