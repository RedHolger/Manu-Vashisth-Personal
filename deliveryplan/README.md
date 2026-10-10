# DeliveryPlan — delivery tracker for a synthetic launch (role 25)

Cycle detection, critical path, date-shift drift, RAID, weekly status.
FastAPI + React/TS. Synthetic data; no programme ownership claims.

## Setup

```
python -m unittest discover -s tests -v   # 10 tests (.venv-builds: fastapi, httpx)
cd ui && npm install && npm run build
```

## Layout

- `SPEC.md`, `CHARTER.md`.
- `backend/plan.py` (graph math), `backend/api.py` (FastAPI).
- `ui/` (React board/milestones/RAID/weekly; view.test.ts).
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
