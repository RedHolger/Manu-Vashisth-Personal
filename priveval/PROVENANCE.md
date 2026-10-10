# PROVENANCE — priveval sources

- No P05 code copied. Control principles aligned with the inspected P05 design
  (`reference/external/projects/P05-evidencerag/`): tenant-first filtering
  before scoring, read-only tool allowlist, serve-time re-authorization, frozen
  attack/benign datasets with denominators. The BM25 scorer, store schema,
  canary fixtures and metrics here are newly written (stdlib + sqlite3).
- Attack patterns informed by P05's `attacks.py` shapes (instruction-carrying
  documents, cross-tenant read attempts) but all texts are new synthetic
  fixtures containing no real data.
