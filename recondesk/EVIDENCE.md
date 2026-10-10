# ReconciliationDesk — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 stdlib only. Deterministic
(frozen as-of 2026-10-08; no randomness).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 6/6 OK.
- `python report.py` → match 2/3, open_base=9060 minor (€90.60), 2 exceptions.

## Measured behavior (fixture ledger)

- FX: GBP 3333 → 3900 base (3899.61 half-up); USD 5000 → 4600; 1¢ USD → 1 (half-up, not banker's).
- Allocation: INV-01/INV-02 matched; INV-03 partial (open 1560); INV-04 open.
- Exceptions: PAY-D duplicate, PAY-E unmatched; overpayment path tested.
- Aging: INV-04 18d → 1–30; INV-03 99d → 90+.
- Tie-out: invoiced 26000 = open 9060 + allocated 16940 (asserted in test).

## Claim basis for CV 29 (role 29 only)

- "Built a Python/SQL invoice-payment reconciliation lab on hand-calculated
  fixtures: multi-currency allocation with half-up FX, duplicate/partial/
  overpayment handling, exception aging and a tie-out executive report."
- "Educational tool; no financial advice or banking-system claims."
