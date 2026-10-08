'use strict';
// P14-01: mandatory vs optional labeled; no university requirements invented.
const a = require('node:assert/strict');
const fs = require('node:fs');

const text = fs.readFileSync('REQUIREMENTS.md', 'utf8');
a.ok(/Mandatory core/i.test(text) && /Optional enrichment/i.test(text));
a.ok(/SUGGESTION/i.test(text) || /optional/i.test(text));
a.ok(/not any university|no university|generic curriculum/i.test(text));
for (const invented of ['MIT 6.', 'Stanford CS', 'CMU 15-', 'requires CS', 'per the catalog', 'University requires']) {
  a.ok(!text.includes(invented), 'invented university requirement: ' + invented);
}
a.ok(/90-minute|Thursday/i.test(text));
console.log('PASS: P14-01 requirements checks (mandatory vs optional, generic, no university invention)');
