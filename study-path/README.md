# StudyPath — prerequisite-aware study planner

Plan study around real prerequisite chains: topics complete only with
completed prerequisites, undoing a prerequisite with finished dependants is
refused, scheduling conflicts stay visible (never silently merged), and bad
imports preserve your existing plan. Progress persists locally with safe
fallback. Static HTML/JS, `node` for tests.

## Run it

```sh
node test_core.js && node test_requirements.js && node test_schedule.js && node test_design.js
```

Then open `index.html` in a browser. The curriculum is generic (pixels →
filters → edges, plus optional enrichment that can never block) — not any
university's requirements. Design decisions, rejected alternatives and
accessibility reasoning are written down; no user research was conducted and
none is presented. User testing with consenting participants is the open
next step.

## Limits

Author-judgment design without user input (stated, not hidden). Browser
flows and keyboard/screen-reader validation need a browser.
