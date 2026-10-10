# ProcessCheck — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, .venv-builds Python 3.14.7 + numpy 2.2.6.
Deterministic (seed 3; frozen CSV).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 6/6 OK.
- `python report.py` → flagged [B07, B08], Cpk 1.387.

## Claim basis for CV 30 (role 30 only)

- "Built a batch-quality lab on synthetic fixtures: unit/null validation with
  traceability, X-bar/R control charts flagging seeded shifts, capability
  estimates under stated assumptions and a corrective-action log (6 tests)."
- "Teaching scope; no GMP or medical-device regulatory validation."
