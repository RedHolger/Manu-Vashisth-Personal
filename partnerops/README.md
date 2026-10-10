# PartnerOps Analytics — partner pipeline + enablement KPIs (role 03)

Hand-calculated fixtures, denominators, missing-data rules, data dictionary,
deterministic narrative + static dashboard. Synthetic data; no SAP involvement.

## Setup (local PostgreSQL 16; psycopg in .venv-builds)

```
./pg.sh   # cluster, seed, 6 tests, KPI run -> results/kpis.json + report.html
```

## Layout

- `SPEC.md` (KPIs, rules, hand calcs), `PROVENANCE.md` (P07/P08 checked).
- `sql/schema.sql`, `sql/seed.sql`, `sql/queries.sql` (canonical, marker-split).
- `kpi.py`, `tests/test_kpis.py`, `pg.sh`.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
