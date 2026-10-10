# DeliveryPlan — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64; .venv-builds Python 3.14.7 + FastAPI 0.143.0
(TestClient); Node v22.12.0, Vite 5.4.21, React 18.3.1, TS 5.6.3.

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 10/10 OK (graph 5 + API 5).
- UI: 2/2 TS tests OK; `npm run build` tsc + vite green.

## Measured behavior (hand-verified)

- Seed acyclic; T1→T8 edge rejected with cycle path shown (422).
- Critical path [T1,T2,T4,T8] = 19 days.
- M1 drift −2 baseline; shifting T2 +3d cascades to T4/T5/T8, drift +1.
- Weekly: 2/7 done; narrative matches state counts; audit-style logs kept.

## Claim basis for CV 25 (role 25 only)

- "Built a delivery tracker for a synthetic launch with cycle detection,
  critical-path and date-shift analysis, RAID register, milestone-drift and
  weekly reports (10 backend + 2 frontend-helper tests), plus a React status board."
- "Training scope only; no real programme ownership."
