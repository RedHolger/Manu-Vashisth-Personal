# Accessibility review — P13 OpsConsole (static; browser/AT BLOCKED)

Method: static audit (`a11y.js`, 12 checks) + manual source review. No
browser engine, screen reader or automated checker (axe) was available, so
keyboard walkthrough, SR announcement verification and checker certification
are BLOCKED and explicitly not claimed. Automated static checks alone do not
certify accessibility — this file is the manual half, and both halves stop
at the browser gate.

## Problems found (static) → fixes (verified by re-audit)

1. **Implicit-only labels (0/3 explicit).** The three toolbar controls relied
   on wrapping `<label>` alone. Some AT combinations announce explicit
   `for`/`id` pairs more reliably.
   → Fix: added `for="q|state|file"` to the wrapping labels (kept wrapping
   for layout). Re-audit: 3/3 explicit. Files: `index.html`.
2. **No skip link.** Keyboard users tabbed from the toolbar straight into a
   potentially long incident list with no bypass.
   → Fix: first-focusable `Skip to incident list` link → `#list`
   (`tabindex="-1"`), visually hidden until `:focus-visible`, with the
   project's 3px focus style. Re-audit: skip-link PASS. Files: `index.html`,
   `style.css`.

Audit went 10/12 → **12/12 PASS** (contrast: body 13.36, button 11.48,
focus 4.14 vs 4.5/4.5/3.0 minima).

## Manual source review (static; needs browser to confirm)

- **Focus order:** DOM order is skip → search → state → import → demo →
  status → list. Logical; no positive tabindex anywhere (verified by grep).
  Real Tab walkthrough BLOCKED (no browser).
- **Status announcements:** `#status` has `role="status"` + `aria-live`
  polite; import errors and counts route through it. SR announcement timing
  BLOCKED (needs SR).
- **Meaning:** state/freshness are text (`OPEN | STALE | …`), never
  color-only. Contrast passes (above).
- **No keyboard traps:** no modal, no custom widget; native inputs/buttons/
  select/details only. Confirm by keyboard BLOCKED.

## Remaining gates (all BLOCKED)

Real keyboard-only run-through, screen-reader pass, axe/browser checker, and
the P15 Study-A usability sessions (see `USABILITY_PLAN.md`). This review
must not be cited as certification.
