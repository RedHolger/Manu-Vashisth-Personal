# OpsConsole

A dashboard for investigating background jobs and incidents. It shows job history, paginated records and audit events, with role-scoped retry and cancel actions. Version checks reject stale changes, while idempotent requests make retries predictable.

The backend uses isolated, seeded adapters. That keeps investigations repeatable without connecting the UI to operational services.

## Run locally

Start the standard-library Python API from `backend/`:

```bash
python3 server.py 8471
```

In another terminal, run from `frontend/`:

```bash
npm ci
npm run build
npm run dev
```

Vite serves the UI on port 5174 and proxies `/api` to the backend.

From the project root:

```bash
python3 -m unittest discover -s tests -v
python3 demo_investigation.py
```

The scripted investigation writes `results/demo.json`. Frontend logic tests can be run from `frontend/` with Node 22 and `node --experimental-strip-types --test tests/*.test.ts`.

See `backend/adapters.py` for the seeded stores, [SPEC.md](SPEC.md) for action semantics and [EVIDENCE.md](EVIDENCE.md) for saved checks.
