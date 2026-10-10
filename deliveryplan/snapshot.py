"""Snapshot the seeded plan state: weekly report, milestone drift, charter.
Deterministic; writes results/snapshot.json. Run: python snapshot.py"""
import json
import sys

sys.path.insert(0, "backend")
import plan  # noqa: E402

state = plan.seed()
path, length = plan.critical_path(state["tasks"])
snap = {
    "critical_path": path,
    "critical_length_days": length,
    "weekly": plan.weekly_report(state),
    "milestone_drift": {m: plan.milestone_drift(state, m) for m in state["milestones"]},
    "charter_scope": "synthetic training scope; no real programme",
}
json.dump(snap, open("results/snapshot.json", "w"), indent=2)
print(json.dumps(snap, indent=2))
