# ReconciliationDesk

An invoice/payment reconciliation exercise with partial payments, duplicates, overpayments and foreign-exchange allocation. Money calculations use `Decimal` with half-up rounding, and the expected totals are worked out by hand in the fixture definitions.

The report groups exceptions by age and ties allocated and outstanding amounts back to the input ledger. The goal is to make a mismatch explainable rather than hide it inside a final total.

## Run the checks

Use Python 3; no additional packages are required.

```bash
python3 -m unittest discover -s tests -v
python3 report.py
```

Outputs are `results/report.json` and `results/report.html`. `src/ledger.py` contains allocation, FX and aging logic. [SPEC.md](SPEC.md) defines the business rules and hand calculations.

All ledger entries are synthetic. This is a reproducible accounting-data exercise, not a connection to a bank or live treasury system.
