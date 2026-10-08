'use strict';
// P13-03 static accessibility audit (no browser engine available).
//
// Checks semantic HTML/ARIA/keyboard/contrast statically against
// index.html + style.css. This is NOT a certification: real keyboard,
// screen-reader and automated-checker (axe) verification needs a browser and
// is BLOCKED. Findings here are real static issues, fixed and documented in
// A11Y_REVIEW.md; browser/AT testing stays an explicit gate.
const fs = require('node:fs');
const path = require('node:path');

function luminance(hex) {
  const c = hex.replace('#', '');
  const rgb = [0, 2, 4].map(i => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
}

function contrast(fg, bg) {
  const l1 = luminance(fg), l2 = luminance(bg);
  const [hi, lo] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

function audit(dir = __dirname) {
  const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
  const css = fs.readFileSync(path.join(dir, 'style.css'), 'utf8');
  const findings = [];
  const check = (name, ok, detail) => findings.push({ check: name, pass: !!ok, detail });

  check('html-lang', /<html[^>]*\blang=/.test(html), 'lang attribute');
  const inputs = [...html.matchAll(/<(input|select|textarea)[^>]*>/g)];
  const labeled = inputs.filter(tag => {
    const id = (/id="([^"]+)"/.exec(tag[0]) || [])[1];
    const forLabeled = id && new RegExp(`for="${id}"`).test(html);
    return forLabeled; // explicit for/id only (wrapping alone is weaker)
  });
  check('explicit-labels', inputs.length > 0 && labeled.length === inputs.length,
    `${labeled.length}/${inputs.length} controls have explicit for/id labels`);
  const buttons = [...html.matchAll(/<button[^>]*>(.*?)<\/button>/gs)];
  check('button-names', buttons.length > 0 && buttons.every(b => b[1].trim().length > 0),
    'every button has text');
  const imgs = [...html.matchAll(/<img[^>]*>/g)];
  check('img-alt', imgs.every(t => /\balt=/.test(t[0])), `${imgs.length} imgs, all with alt`);
  const headings = [...html.matchAll(/<h([1-6])/g)].map(m => +m[1]);
  check('heading-order', headings[0] === 1 && headings.every((h, i) => i === 0 || h <= headings[i - 1] + 1),
    'h1 first, no skipped levels');
  check('landmarks', /<header[\s>]/.test(html) && /<main[\s>]/.test(html), 'header+main');
  check('skip-link', /href="#main"|href="#list"|class="skip/.test(html), 'skip link to content');
  check('status-live', /role="status"/.test(html) && /aria-live="polite"/.test(html), 'status role+live');
  check('focus-visible', /:focus-visible/.test(css), 'focus-visible styles');
  const pairs = [
    ['body text', '#182a3d', '#f2f5f9', 4.5],
    ['button text', '#ffffff', '#163b60', 4.5],
    ['focus outline', '#bb5c00', '#f2f5f9', 3.0],
  ];
  for (const [name, fg, bg, min] of pairs) {
    const ratio = contrast(fg, bg);
    check('contrast-' + name, ratio >= min, `${fg} on ${bg} = ${ratio.toFixed(2)} (needs ${min})`);
  }
  return findings;
}

module.exports = { audit, contrast };
