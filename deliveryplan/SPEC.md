# DeliveryPlan — SPEC (Milestone 1)

Scope: delivery tracker for a SYNTHETIC payments launch, for role 25
(Mastercard program management). FastAPI + React/TS. No real programme,
no employer data.

## Domain (seeded, deterministic)

- 8 tasks: id, title, team, owner, status, start_date, duration_days, deps[].
  End = start + duration (computed, never stored inconsistently).
- Milestones: name, planned_date, prereq task ids, exit criteria text.
- Decisions log (append-only), RAID register (type risk/assumption/issue/
  dependency + owner + rating high/med/low), stakeholders map.
- Frozen TODAY = 2026-10-08 for drift math.

## Graph rules (pure Python, unit-tested with hand calcs)

- Adding a dependency that creates a cycle → rejected (422, cycle path shown).
- Critical path = longest duration path; seed CP = [T1,T2,T4,T8] = 5+8+4+2 = 19d.
- Date shift: moving a task shifts dependents (cascade by dependency, keeping
  durations); milestone projected = max prereq end; drift = projected − planned.
  Seed: M1 planned 09-22, projected 09-20 → drift −2; shift T2 +3d → drift +1.

## API (FastAPI, TestClient-tested)

- GET /tasks, /milestones, /decisions, /raid, /charter, /stakeholders.
- POST /tasks/{id}/deps {dep} (cycle → 422), POST /tasks/{id}/shift {days},
  POST /tasks/{id}/status {status}, POST /decisions, POST /raid.
- GET /reports/milestones (drift per milestone), GET /reports/weekly
  (counts by status, drift, top risks, narrative) — both computed from state;
  tests assert traceability (report numbers == recomputed).

## UI + acceptance

React/TS: board by status, milestone drift list, RAID table, weekly report
view, role note (viewer demo; mutations open in demo, stated). TS tests for
drift-label + status-group helpers. No fabricated programme ownership
(CHARTER.md states synthetic training scope).
