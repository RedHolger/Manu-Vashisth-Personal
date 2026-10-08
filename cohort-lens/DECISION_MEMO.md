# Decision memo — P08 CohortLens (descriptive only)

- Data cutoff (`as_of`): `2026-01-20T00:00:00Z`
- Cohort key: Monday of signup week, UTC. Segment source: `user_segments`
  side table; unmapped users are `unknown` (their own row, never zero).
- Windows: activation in `[signup, signup+7d)`; week-1 active in
  `[signup+7d, signup+14d)`. Denominators admit only complete windows;
  incomplete windows render as `n/a`.
- Source table: `segments.py:segment_cohorts + segments.sql (same contract)`;
  dashboard: `dashboard.build_dashboard()`; fixture: 6 events, 3 users,
  1 signup cohort (`2026-01-05`).

## Observed table (numerator/denominator = rate)

| cohort | segment | users | activated | week-1 retained |
|---|---|---|---|---|
| 2026-01-05 | organic | 1 | 1/1 = 1.000 | 1/1 = 1.000 |
| 2026-01-05 | paid | 1 | 0/1 = 0.000 | 0/1 = 0.000 |
| 2026-01-05 | unknown | 1 | 1/1 = 1.000 | 0/1 = 0.000 |

## Reading (descriptive associations, not causal)

- Organic shows a higher descriptive activation and week-1 retention than
  paid on this tiny fixture (1/1 vs 0/1 in both windows). This is an
  observed association in 3 users; it does not establish that the segment
  label influences, explains, or predicts retention for other users.
- Unknown behaves like organic on activation (1/1) and like paid on week-1
  (0/1). Unknown means "no mapping supplied", not "zero" and not a real
  acquisition channel.
- No incomplete window enters any denominator above: every row shown is
  fully mature at this cutoff. Young-cohort views render `n/a`.

## Decision

Do not ship a segment-targeted change on this evidence. The denominators
are 1 per row; sampling variation dominates. If a product change is
proposed, evaluate it as a randomized experiment through P07 (predeclared
estimand, exposure rules, sensitivity bounds) after collecting sufficient
data. Revisit this memo only with a larger fixture and a new cutoff.

## Limitations

- Synthetic fixture (3 users); no licensed or product data.
- Segments have no history; relabeling rewrites past cohorts.
- Only activation + week-1 windows; no week-2/4 grid.
- Dashboard is static HTML; no authentication, no live refresh.
