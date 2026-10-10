# PartnerOps Analytics — SPEC (Milestone 1)

Scope: partner pipeline + enablement KPIs with denominators, missing-data
rules and a data dictionary, for role 03 (SAP partner business operations).
Python + local PostgreSQL 16 (psycopg). No SAP system involved.

## Overlap check

P07 (experiment assignment/effects) and P08 (activation/retention cohorts)
cover different domains; no code reused (see PROVENANCE.md).

## Schema (`sql/schema.sql`)

partners(id, name, tier, region); deals(id SERIAL, ext_id TEXT, partner_id,
stage TEXT NULL ['won','lost','open', NULL→unknown], amount_eur INT NULL,
created DATE); enablement(partner_id, module, done BOOL).
Unique constraint on deals(ext_id) is deliberately ABSENT — duplicates arrive
and are deduped in the KPI layer (counted, earliest kept).

## KPIs + denominators + missing-data rules

- win_rate = won / (won + lost); open/unknown excluded (denominator stated).
- avg_won_size = AVG(amount) over won, non-null, non-outlier deals.
- outlier: won amount > 3 × median(won amounts) → flagged, excluded, counted.
- NULL amount → excluded from avg, counted as missing_amount.
- NULL stage → 'unknown' bucket, listed, excluded from win rate.
- enablement_rate = completed / assigned modules.
- duplicate ext_id rows → deduped (earliest id kept), counted.

## Hand-calculated fixtures (asserted in tests)

Seed (SPEC keeps the full table; key expectations): won {D01 10000, D02 20000,
D04 5000, D07 NULL, D09 500000-outlier}, lost {D03, D06}, open {D05, D11},
unknown {D10}, dup {D01×2}, missing amounts {D07, D11}.
Expected: win_rate 5/7; avg 35000/3 = 11666.67; outlier 1 (D09);
missing_amount 2; unknown_stage 1 (D10); duplicates 1; enablement 3/5 = 60%.

## Outputs

`kpi.py` → `results/kpis.json` + `results/report.html` (static dashboard with
data-dictionary section + deterministic narrative paragraph). Executive report
reconciles: every excluded row is counted somewhere.
