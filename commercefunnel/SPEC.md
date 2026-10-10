# CommerceFunnel Lab — SPEC (Milestone 1)

Scope: synthetic e-commerce funnel + fulfilment dashboard with cohort analysis
and a PROPOSED (not run) experiment, for role 16 (Tesco Online). stdlib +
sqlite3. No real shop data.

## Overlap check

P08 CohortLens covers activation/retention cohorts with SQL parity; this build
covers purchase funnels, substitutions and delivery slots — different domain,
no code reused (see PROVENANCE.md).

## Events

`events(user_id, event, product, ts, session_id, extra)` where event in
{view, basket, purchase, stockout, substitute, slot_book, delivered} and extra
holds substitute target / on-time flag. Dedup key: (session_id, event, product,
ts) — exact replays collapse, count reported.

## Metrics (all with denominators + Wilson 95% CI)

- Funnel (distinct users): view→basket, basket→purchase, view→purchase.
- SEMANTICS NOTE (audit-driven): these are SET-INTERSECTION user overlaps, not
  time-ordered within-session/product/window conversions (e.g. U4 purchased
  without a basket event and still counts in view→purchase). Zero denominators
  yield explicit null rates (`frac: None` + `unavailable` reason, CI [0,1]),
  never a crash and never a silent 0.0.
- Substitution acceptance: accepted / stockouts.
- Slot on-time rate: on-time / delivered.
- Weekly acquisition cohorts (Monday of first-seen week): purchase rate by cohort.
- Primary metric for the proposal: view→purchase; guardrails: substitution
  acceptance, on-time rate.

## Hand-calculated fixtures (asserted in tests)

7 users, 2 cohorts. Viewed U1–U7 (7); basketed U1,U2,U3,U5,U7 (5);
purchased U1,U3,U4,U5,U7 (5, incl. U4 with no basket); one duplicate view
(U4, same session) deduped; substitutions 1/1 (U3 B→C); slots on-time 2/3
(U5 late); cohorts W1 (U1–U5) 4/5, W2 (U6–U7) 1/2.
Expected: view→basket 5/7, basket→purchase 4/5, view→purchase 5/7,
deduped_events 1, sub_rate 1/1, ontime 2/3.

## Outputs

`report.py` → `results/report.json` + `results/report.html`; `experiment.md`
(proposal only — hypothesis, unit, primary/guardrails, analysis plan, NOT RUN).
No conversion uplift invented anywhere.
