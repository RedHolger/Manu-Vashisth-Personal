# ReconciliationDesk — invoice/payment reconciliation lab (role 29)

Hand-calculated fixtures, Decimal half-up FX, exception aging, static
working-capital dashboard. Educational; no advice, no bank systems.

## Setup (.venv-builds or system python3; stdlib only)

```
python -m unittest discover -s tests -v   # 6 tests
python report.py                           # -> results/report.json + report.html
```

## Layout

- `SPEC.md` (business definitions + hand calcs), `datasets/fixtures.json`.
- `src/ledger.py` (sqlite store, Decimal FX, allocator, aging, report).
- `report.py`, `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
