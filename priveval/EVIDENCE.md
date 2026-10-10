# PrivacyEval — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 stdlib + sqlite3 only.
Deterministic (no randomness; frozen datasets).

## Commands (exit 0)

- `python measure.py` → `results/measure.json` (reproduced identically).
- `python -m unittest discover -s tests -v` → 8/8 OK.

## Measured behavior

- Baseline: leakage 5/12 (CI 0.19–0.68), attack success 10/12 (CI 0.55–0.95),
  benign 7/8, stale v1 retrievable, revoked grant still answers.
- Controls: leakage 0/12, success 0/12 (CI 0–0.24), benign 8/8, v1 filtered
  with v2 ("30 days") served, revoked grant abstains.
- Utility note: controls (8/8) beat baseline (7/8) — unfiltered corpus
  distracts ranking; reported, not hidden.

## Claim basis for CV 33 (role 33 only)

- "Built an isolated canary-leakage harness comparing unprotected retrieval
  against tenant-scoped, re-authorized controls: 0/12 attacks succeed under
  controls vs 10/12 unprotected, benign utility 8/8, with stale-cache and
  revocation checks."
- "Synthetic canaries only; authorization controls, not differential privacy."

## Repair 2026-10-08 (Item 6: real stale-cache, audit-found)
- Audit noted the "stale" check tested revoked-version visibility without a
  real cache. Added src/cache.py (version-tagged entries; naive vs validated
  policies) plus a mid-run revocation scenario: naive serves the revoked text
  (stale-served), validated blocks. New unit + acceptance tests.
- Reran: 12/12 tests OK; transcript in results/lastrun.log. CV33 "stale-cache"
  wording now describes implemented behavior; no CV text change needed.
- Toy boundaries from the audit (extractive quoter, verdict-flag tools, small
  frozen sets) remain in LIMITATIONS.md and are unchanged by this repair.
