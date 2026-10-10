# EngineeringEvidence — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 stdlib + sqlite3, TeX Live 2025
pdflatex. Deterministic (seeded fixtures; no randomness).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 6/6 OK.
- `python review_package.py` → pdflatex exit 0; review.pdf (68,672 bytes);
  gaps printed: orphans=[REQ-07], conflicts={REQ-03:[B,C]},
  no-evidence=[T-05], pending=[T-03b], failed=[T-06].

## Claim basis for CV 28 (role 28 only)

- "Built a software-only requirements traceability tool for a fictional cabin
  modification: revision-aware matrix, orphan/conflict/incomplete-evidence
  checks (6 tests) and a compiled synthetic review package."
- "No stress analysis, certification, or EASA competence claims."
