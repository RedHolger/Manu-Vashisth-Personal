# CommerceFunnel — LIMITATIONS

- 26 synthetic events, 7 users; toy scale, not retail analytics.
- The experiment is a design document: zero traffic, zero results. Citing it
  as experience means design experience only (CV wording reflects this).
- No real shopper, revenue, or logistics data.
- Local-machine determinism only.
- Supports role 16 only as funnel/analysis-method work.

## Repair 2026-10-08 (F3: zero denominators, audit-found)
- Empty/view-only/basket-only stores raised ZeroDivisionError. Now all rates
  return explicit null (`frac: None` + reason) with degenerate CI [0,1];
  report renders "n/a (reason)". 0/1-style defined rates unchanged.
- Funnel steps measure user-set overlap, NOT time-ordered conversion within a
  session, product, or window. Stated here and in SPEC.md.
