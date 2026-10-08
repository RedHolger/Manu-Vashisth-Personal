'use strict';
// P13-03/04: static a11y green with documented fixes; usability honestly BLOCKED.
const a = require('node:assert/strict');
const fs = require('node:fs');
const a11y = require('./a11y.js');

const findings = a11y.audit();
a.equal(findings.filter(f => f.pass).length, findings.length);
a.ok(Math.abs(a11y.contrast('#000000', '#ffffff') - 21) < 0.1);
const review = fs.readFileSync('A11Y_REVIEW.md', 'utf8');
a.ok(review.includes('skip link') || review.includes('Skip'));
a.ok(review.includes('explicit'));
a.ok(review.includes('BLOCKED'));
a.ok(review.includes('12/12'));
const plan = fs.readFileSync('USABILITY_PLAN.md', 'utf8');
a.ok(plan.includes('BLOCKED'));
a.ok(!/finding:\s*\S+\s*completed/i.test(plan) || plan.includes('no findings'));
console.log(`PASS: P13-03/04 checks (a11y ${findings.length}/${findings.length} static, review documents fixes, usability BLOCKED); browser/AT/study pending`);
