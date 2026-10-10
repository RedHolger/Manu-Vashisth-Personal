# PROVENANCE — opsconsole sources

- Semantics aligned with inspected snapshots (not copied):
  `reference/external/projects/P04-flowledger` (idempotent submissions,
  bounded retries, audit trail) and `reference/external/projects/sre-portfolio`
  (RecoverOps incident/action state, dedup). All adapter/API/UI code here is
  newly written against in-memory stores; no snapshot code vendored.
- Frontend stack: React + TypeScript via Vite (npm registry packages only).
