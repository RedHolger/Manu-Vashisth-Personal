# PartnerOps — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 + psycopg 3.3.6, local
PostgreSQL 16 (initdb cluster, port 55434). Deterministic (seeded fixtures).

## Commands (exit 0)

- `./pg.sh` → 6/6 tests OK + KPI run: win 5/7 (71.43%), avg EUR 11666.67
  over 3 deals, 1 outlier, 2 missing amounts, 1 unknown stage, 1 duplicate,
  enablement 3/5 (60.0%).

## Claim basis for CV 03 (role 03 only)

- "Built a partner-pipeline analytics lab on hand-calculated fixtures: win
  rate with denominators, outlier/missing-data rules, enablement tracking
  and a reconciled executive report with data dictionary."
- "Synthetic data; no SAP-system claims."
