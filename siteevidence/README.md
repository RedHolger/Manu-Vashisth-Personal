# SiteEvidence

A document-coordination tool for RFIs and inspections. Each record has an owner, revision, due date and evidence links. The tracker identifies overdue items, missing evidence and revision mismatches, then collects them into a weekly report and handover package.

The example records describe a fictional construction project. They exercise the paperwork workflow without representing an actual site inspection.

## Backend and handover report

Use Python 3 with FastAPI installed:

```bash
python3 -m unittest discover -s tests -v
python3 handover.py
```

The report is written to `results/handover.json` and `results/handover.html`. Domain logic is in `backend/store.py`, with FastAPI routes in `backend/api.py`.

## Frontend

From `ui/`, with Node.js installed:

```bash
npm ci
npm run build
npm run dev
```

The development UI uses port 5177. Run its helper tests with Node 22 using `node --experimental-strip-types --test tests/*.test.ts`. See [SPEC.md](SPEC.md) for record rules and [EVIDENCE.md](EVIDENCE.md) for saved checks.
