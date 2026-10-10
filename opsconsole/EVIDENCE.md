# OpsConsole — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64; backend system Python 3.14.7 stdlib; frontend
Node v22.12.0, Vite 5.4.21, React 18.3.1, TypeScript 5.6.3 (npm registry).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 11/11 API tests OK.
- `node --experimental-strip-types --test "tests/*.test.ts"` → 12/12 frontend
  tests OK (7 helper + 5 live-client: keyed cancel, replay, stable-key retry,
  key policy, ambiguity policy).
- `npm run build` → tsc clean + vite bundle (dist/ 146 kB JS).
- `python demo_investigation.py` → 7-op transcript, failed job 1 retried as
  run 1000 (same key replayed, one run), audit verified, viewer 403 proven.

## Claim basis for CV 21 (role 21 only)

- "Built a React/TypeScript job-history and incident dashboard over isolated
  adapters with role-scoped actions, audit, pagination, stale-version checks
  and idempotent retry/cancel (11 API + 12 frontend tests, scripted investigation demo)."
- "Synthetic data only; no live-service exposure."

## Repair 2026-10-08 (F2: idempotency scoping, audit-found)
- Audit reproduced: a retry key reused on another job returned the first
  job's result (global key store, no scope), and cancel had no replay
  handling (repeat returned 409). No locking around check/mutate/store.
- Fix: keys scoped to one (job_id, action); replay-first ordering under a
  mutex covering the whole check/validate/mutate/store/audit sequence;
  cross-scope reuse returns 409 with the original scope; cancel requires a
  key and replays stored success; non-numeric If-Match returns 409 instead
  of crashing.
- New tests: cross-job reuse rejected (job untouched), action mismatch
  rejected, cancel replay (one version bump, one audit row), key required
  on cancel, 10-thread concurrent retry (one run, one audit, same run_id).
- Reran: 11/11 API tests OK; demo_investigation.py exit 0; transcript in
  results/lastrun.log. CV21's "idempotent retry/cancel" wording now matches
  the implementation; X-Role demo-auth limitation unchanged.

## Repair 2026-10-08 R1 (frontend cancel, audit-found)
- The frontend sent no Idempotency-Key on cancel (HTTP 400 after the backend
  repair). Fixed: api.cancel(id, version, key) sends the key; App uses
  makeKey(action, id, version) — stable per logical action — with one safe
  retry on ambiguous outcomes (network/5xx reuse the same key; 4xx decisive).
- New tests/frontend/tests/client.test.ts drives the ACTUAL api client against
  a live backend: keyed cancel 200 + version bump, replay replays, stable-key
  retry shares run_id, key policy + ambiguity mapping units.
