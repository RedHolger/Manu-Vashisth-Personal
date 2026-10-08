'use strict';
// P13-02: malicious strings stay text; robust states hold without a browser.
const a = require('node:assert/strict');
const sec = require('./security.js');
const robust = require('./robust.js');

const evil = '<script>alert(1)</script><img src=x onerror=alert(2)>&"\'';
const esc = sec.escapeHtml(evil);
// No angle brackets survive, so no tag can form; the payload stays text.
a.ok(!esc.includes('<') && !esc.includes('>'));
a.ok(esc.includes('&lt;script&gt;') && esc.includes('&amp;'));
const html = sec.renderIncidentToString({ id: evil, service: evil, state: 'OPEN', updated: '2026-01-01T00:00:00Z', events: [{ at: '2026-01-01T00:00:00Z', text: evil }] });
a.ok(html.includes('&lt;script&gt;') && !html.includes('<script>alert'));
a.ok(!html.includes('<img src=x'));
a.deepEqual(sec.auditSources(), []);

const big = Array.from({ length: 1200 }, (_, i) => ({ id: 'i-' + i }));
const sliced = robust.sliceList(big);
a.equal(sliced.rendered.length, 500);
a.equal(sliced.truncated, 700);
const st = robust.parseUrlState('http://x/?q=api&state=OPEN');
a.deepEqual(st, { q: 'api', state: 'OPEN' });
a.equal(robust.parseUrlState('http://x/?state=BOGUS').state, 'ALL');
a.ok(robust.serializeUrlState('a b', 'OPEN').includes('q=a+b'));
const cur = [{ id: 'keep', service: 's', state: 'OPEN', updated: '2026-01-01T00:00:00Z', events: [] }];
const bad = robust.importState(cur, 'not json{{{');
a.equal(bad.rows, cur);
a.ok(bad.error);
const good = robust.importState(cur, JSON.stringify([{ id: 'n', service: 's', state: 'UNKNOWN', updated: '2026-01-01T00:00:00Z', events: [] }]));
a.equal(good.rows[0].id, 'n');
a.equal(robust.freshnessBucket({ updated: '2026-01-01T00:00:00Z' }, Date.parse('2026-01-01T00:00:00Z') + 60001), 'STALE');
a.equal(robust.freshnessBucket({ updated: '2026-01-01T00:00:00Z' }, 0), 'CLOCK_SKEW');
console.log('PASS: P13-02 hardening checks (escaping, audit, slice, URL, import, freshness); browser execution BLOCKED');
