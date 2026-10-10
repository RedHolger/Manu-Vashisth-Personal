# OpsConsole — SPEC (Milestone 1)

Scope: job/incident investigation dashboard for role 21 (Horizon Quantum).
Backend: stdlib Python REST API over isolated in-memory adapters with
FlowLedger/RecoverOps-aligned semantics (idempotent submit/retry, dedup,
audit). Frontend: React + TypeScript (Vite), role-gated actions. No
live-service exposure; all data synthetic.

## API (loopback; `X-Role: viewer|operator|admin`, default viewer)

- GET /api/jobs?status=&page=&per_page= (per_page ≤ 50) → paged list.
- GET /api/jobs/{id} → job {id,name,status,version,runs}.
- POST /api/jobs/{id}/retry — operator/admin; needs Idempotency-Key +
  If-Match version. Failed-only (else 422). KEY CONTRACT (repaired 2026-10-08
  after an audit found cross-job aliasing): a key is scoped to exactly one
  (job_id, action). Replay is checked FIRST under a lock: a known key returns
  its stored immutable response verbatim (no revalidation, no new mutation,
  no new audit). A known key on a different (job, action) is a client bug and
  returns 409 — never cross-applied. Unknown keys proceed to version/state
  validation, then the whole check/mutate/store/audit sequence runs atomically
  under one mutex (ThreadingHTTPServer serves concurrent connections).
- POST /api/jobs/{id}/cancel — operator/admin; needs Idempotency-Key +
  If-Match; queued/running only; same replay-first key contract as retry
  (repeat with the original key replays the stored success response).
- GET /api/incidents[?severity=], GET /api/incidents/{id} (with actions).
- POST /api/incidents/{id}/actions {text} — operator/admin; audit entry.
- GET /api/audit — admin only (operator/viewer → 403).

## Seed

12 jobs (compile/queue/run lifecycle states across queued/running/failed/done/
canceled), 4 incidents with actions. Deterministic seed script.

## Acceptance mapping

Authorization matrix, pagination bounds, stale-version 409, idempotent retry
(same key, one run), cancel rules, audit completeness — Python API tests.
UI logic (role gating, paging math) — TS unit tests via node strip-types.
`demo_investigation.py` drives a full investigate→retry→verify transcript.
No live services; no production-monitoring claims.
