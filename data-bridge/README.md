# DataBridge — resumable imports that survive crashes

Move paginated HTTP data into Postgres so a killed process resumes instead
of restarting: one transaction per page (rows + quarantine + checkpoint
together), real SIGKILL fault injection, and a head-to-head evaluation of
one-shot vs resumable strategies under identical faults.

## How it works

- CSV/JSON connectors with timeouts, retry caps and `Retry-After` handling
  against a scripted local fixture (429/500/400/invalid/stall).
- PostgreSQL adapter commits each page atomically and exports a row-level
  completeness report.
- The fault matrix kills workers mid-page and post-commit, then resumes and
  compares dataset hashes.

## Run it (needs Docker + Python venv)

```sh
docker compose up -d        # PostgreSQL 16
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -p 'test_*.py'   # 47 tests
```

Recorded: resumable needed 15 fetches / 3 repeated pages / 0 discarded rows
vs one-shot's 21 / 9 / 18 under the same kill schedule; identical dataset
hashes across runs. A 12-row recovery fixture — evidence of correctness
under faults, not throughput.

## Limits

Schema management is connect-time DDL (no migration tool). Timings are
sub-second single-machine figures. No production-scale claims.
