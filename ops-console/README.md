# OpsConsole — incident-evidence viewer

Inspect recorded incident evidence without touching infrastructure: filter by
text/state, URL-stable filters, validated JSON import, STALE/CLOCK_SKEW
freshness, and rendering that keeps malicious strings as text (XSS-safe by
construction, statically audited). Adapts real run-evidence files to rows
marked UNKNOWN (unreviewed) — missing telemetry never becomes a fabricated
recovery. Static HTML/JS, no dependencies beyond `node` for tests.

## Run it

```sh
node test_core.js && node test_adapter.js && node test_hardening.js && node test_a11y.js
```

Then open `index.html` in a browser. Recorded: static accessibility audit
12/12 with two real fixes (explicit labels, skip link); 500-row render cap
with truncation reported; import failures preserve existing rows. Browser
execution, screen-reader testing and usability studies need a browser and
participants — not done here — so this review is not a certification.

## Limits

Unreviewed machine summaries, not triaged incidents. No live backend; live
telemetry integration pending lab access.
