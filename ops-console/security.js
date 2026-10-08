'use strict';
// P13-02 security contract (node-testable, no browser needed).
//
// The shipped app renders via textContent/DOM (never innerHTML with data).
// This module is the testable model of that contract: `escapeHtml` plus a
// string renderer that MUST keep malicious input as text, and `auditSources`
// which statically forbids executable-markup patterns in app.js/index.html.
const fs = require('node:fs');
const path = require('node:path');

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function renderIncidentToString(row) {
  // Mirrors app.js render() as a string so node can assert the contract:
  // every data field escaped; structure only from literals.
  const events = row.events.map(e =>
    '<li>' + escapeHtml(e.at) + ' — ' + escapeHtml(e.text) + '</li>').join('');
  return '<article><h2>' + escapeHtml(row.service) + ' · ' + escapeHtml(row.id) +
    '</h2><p>' + escapeHtml(row.state) + ' | ' + escapeHtml(row.updated) +
    '</p><ol>' + events + '</ol></article>';
}

const FORBIDDEN = [
  [/\.innerHTML\s*=/, 'innerHTML assignment'],
  [/\.outerHTML\s*=/, 'outerHTML assignment'],
  [/document\.write\s*\(/, 'document.write'],
  [/\beval\s*\(/, 'eval('],
  [/on\w+\s*=\s*["'][^"']*javascript:/i, 'javascript: URL handler'],
  [/<script[^>]*src\s*=\s*["']http/i, 'remote script src'],
];

function auditSources(dir = __dirname) {
  const violations = [];
  for (const file of ['app.js', 'index.html']) {
    const text = fs.readFileSync(path.join(dir, file), 'utf8');
    for (const [pattern, name] of FORBIDDEN) {
      if (pattern.test(text)) violations.push({ file, pattern: name });
    }
  }
  return violations;
}

module.exports = { escapeHtml, renderIncidentToString, auditSources };
