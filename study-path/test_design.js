'use strict';
// P14-03/04: decisions documented with alternatives; testing honestly BLOCKED.
const a = require('node:assert/strict');
const fs = require('node:fs');

const design = fs.readFileSync('DESIGN.md', 'utf8');
a.ok(/Decisions/i.test(design) && /Rejected/i.test(design));
a.ok(/Alternative/i.test(design));
a.ok(/No user research was conducted|no interviews/i.test(design));
a.ok(!/persona: \w+ \w+|interviewee \d+ said/i.test(design));
const svg = fs.readFileSync('wireframe.svg', 'utf8');
a.ok(svg.startsWith('<svg') && svg.includes('DESIGN.md'));
for (const f of ['index.html', 'app.js', 'model.js', 'schedule.js']) {
  a.ok(fs.existsSync(f), 'editable source present: ' + f);
}
const plan = fs.readFileSync('UTEST_PLAN.md', 'utf8');
a.ok(plan.includes('BLOCKED'));
a.ok(/0 sessions|0 observations/.test(plan));
a.ok(/consent/i.test(plan) && /limitation|limits/i.test(plan));
console.log('PASS: P14-03/04 checks (design decisions + alternatives, editable source, testing BLOCKED with templates); study pending');
