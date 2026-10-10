# CommerceFunnel — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 stdlib + sqlite3 only.
Deterministic (frozen fixture; no randomness).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 5/5 OK.
- `python report.py` → funnel 5/7, 4/5, 5/7 with CIs; sub 1/1; on-time 2/3;
  cohorts 4/5, 1/2; 1 replay deduped.

## Claim basis for CV 16 (role 16 only)

- "Built an e-commerce funnel lab on synthetic events with deduplicated ingest:
  view→basket→purchase conversion with denominators and uncertainty,
  substitution and on-time fulfilment rates, weekly cohorts and a written-up
  (unrun) experiment proposal with primary/guardrail metrics."
- "No real shopper data; no conversion-uplift claims."
