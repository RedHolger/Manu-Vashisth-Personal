# ReconciliationDesk — SPEC (Milestone 1)

Scope: educational invoice↔payment reconciliation with currencies, settlement,
exceptions and a working-capital report, for role 29 (Citi Services analyst).
stdlib only (sqlite3 for storage, decimal for money). Frozen as-of date.

## Business definitions (also printed atop the report)

- Invoice: {id, counterparty, amount_minor, currency, due_date, status}.
  Amounts in minor units (cents/pence); EUR is the base currency.
- Payment: {id, amount_minor, currency, value_date, ref} where ref names an
  invoice id or is blank (unmatched).
- Match: same invoice ref AND converted amounts equal within tolerance 1 cent
  (tolerance covers FX half-cent rounding, documented per case).
- FX: rates to EUR {USD: 0.92, GBP: 1.17}; conversion rounds HALF-UP to the
  minor unit (decimal module; Python round() is banker's and NOT used).
- Partial: payment < invoice → allocated, remainder stays open (status partial).
- Duplicate: second payment with an already-consumed (invoice, amount) pair →
  exception, never double-allocated.
- Exception aging (days past due vs AS_OF 2026-10-08): current (≤0), 1–30,
  31–60, 61–90, 90+.
- Match rate = matched invoices / matchable invoices, always with denominator.

## Fixtures (hand-calculated, hardcoded in tests/test_ledger.py)

INV-01 EUR 10000 due 2026-09-01 + PAY-A EUR 10000 ref INV-01 → matched.
INV-02 USD 5000 (base 4600: 5000x0.92) due 2026-08-01 + PAY-B USD 5000 →
  matched.
INV-03 GBP 3333 (base round(3333x1.17)=round(3899.61)=3900) due 2026-07-01
  + PAY-C GBP 2000 (base 2340) → partial, open base 3900-2340=1560.
PAY-D duplicates PAY-A (EUR 10000 ref INV-01) → duplicate exception.
PAY-E EUR 500 ref INV-99 (unknown) → unmatched exception.
INV-04 EUR 7500 due 2026-09-20, no payment → open, aging 18 days → bucket 1–30.
INV-02 matched → no aging. INV-03 partial, due 2026-07-01 → aging 99 days → 90+.
Expected: matched 2/3 matchable (INV-01, INV-02; INV-03 partial counts open;
INV-04 has no payment so it is open but outside the match denominator),
open EUR-base = 1560 + 7500 = 9060 minor (EUR 90.60); exceptions: duplicate x1,
unmatched x1, open rows x2 (INV-03 partial, INV-04).

## Report

`report.py` → `results/report.json` + `results/report.html` (static dashboard:
totals by currency + EUR base, exception table with aging, match rate with
denominator, definitions header). No advice, no bank-system claims.
