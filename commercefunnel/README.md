# CommerceFunnel Lab — e-commerce funnel + fulfilment (role 16)

Synthetic events, deduped ingest, funnel/cohort metrics with uncertainty, and
a PROPOSED (never run) experiment. No real shop data, no uplift claims.

## Setup (stdlib only)

```
python -m unittest discover -s tests -v   # 5 tests
python report.py                           # -> results/report.json + report.html
```

## Layout

- `SPEC.md` (metrics, hand calcs), `PROVENANCE.md` (P08 checked, distinct).
- `src/funnel.py`, `datasets/events.json` (26 rows, 1 replay), `experiment.md`.
- `report.py`, `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
