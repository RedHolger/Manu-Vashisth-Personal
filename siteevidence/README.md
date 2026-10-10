# SiteEvidence Demo — RFI/inspection tracker (role 38)

Synthetic construction-paperwork tracker: revisions, owners, due dates,
evidence links, weekly gaps, handover pack. No site, no surveying, no civil
competence — stated everywhere.

## Setup

```
python -m unittest discover -s tests -v   # 8 tests (.venv-builds: fastapi)
python handover.py                        # -> results/handover.{json,html}
cd ui && npm install && npm run build     # tsc + vite
```

TS tests: `node --experimental-strip-types --test "tests/*.test.ts"` (3 tests).

## Layout

- `SPEC.md`, `backend/store.py` (domain), `backend/api.py` (FastAPI).
- `ui/` (React list/badges/weekly), `handover.py`.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
