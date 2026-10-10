# OpsConsole — requirements map

| Requirement (BUILD_PROMPTS opsconsole) | Check | Result |
|---|---|---|
| React/TS dashboard over isolated adapters | frontend/ (Vite build green); backend/adapters.py new code | pass |
| Synthetic compile/queue/run lifecycle | 12 seeded jobs; 4 incidents | pass |
| Role-scoped actions + audit | auth matrix test; audit admin-only test | pass |
| Authorization unit/API tests | test_auth_matrix + auth.test.ts (viewer/operator/admin) | pass |
| Pagination tests | test_pagination + paging.test.ts (slice parity) | pass |
| Stale-state tests | test_stale_version_409 (If-Match) | pass |
| Idempotent retry/cancel tests | test_idempotent_retry, test_cancel, test_retry_rules | pass |
| Demo an investigation | demo_investigation.py: 7 ops, transcript JSON | pass |
| No live-service exposure | loopback only; LIMITATIONS.md | stated |
