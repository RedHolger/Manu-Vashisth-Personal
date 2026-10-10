# OpsConsole — job/incident investigation dashboard (role 21)

Synthetic job-history + incident workflow UI over isolated adapters.
No live services (see LIMITATIONS.md).

## Setup

Backend (stdlib only):
```
cd backend && python server.py 8471   # API on 127.0.0.1:8471
```
Frontend (needs npm once):
```
cd frontend && npm install && npm run build   # tsc + vite -> dist/
npm run dev                                   # serves UI, proxies /api
```
Tests: `python -m unittest discover -s tests -v` (7 API tests);
`node --experimental-strip-types --test "tests/*.test.ts"` in frontend (7 UI-logic tests).
Demo: `python demo_investigation.py` (7-op transcript -> results/demo.json).

## Layout

- `SPEC.md`, `PROVENANCE.md`.
- `backend/adapters.py` (seeded stores), `backend/server.py` (REST API).
- `frontend/src/` (React+TS app), `frontend/tests/` (auth/paging unit tests).
- `demo_investigation.py`, `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
