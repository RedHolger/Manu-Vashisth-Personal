# DeliveryPlan

A launch-planning tool for finding the work that controls a delivery date. Tasks have owners and dependencies; the backend detects dependency cycles, calculates the critical path and reports how date changes affect milestones.

A React board displays the plan, milestone drift and RAID records (risks, assumptions, issues and dependencies). The example launch and its charter are fictional.

## Check the planning logic

Use Python 3 with `fastapi` and `httpx` installed in your virtual environment:

```bash
python3 -m unittest discover -s tests -v
```

For the frontend, install Node.js and run from `ui/`:

```bash
npm ci
npm run build
npm run dev
```

The frontend development server uses port 5176. `backend/plan.py` contains the dependency calculations; `backend/api.py` exposes them through FastAPI. The UI's data wiring should be checked before treating a browser interaction as a persisted API operation.

[SPEC.md](SPEC.md) defines the calculations and [CHARTER.md](CHARTER.md) describes the sample launch. Saved checks are in [EVIDENCE.md](EVIDENCE.md).
