"""Isolated job/incident stores with FlowLedger/RecoverOps-aligned semantics.
New code; principles only (see PROVENANCE.md)."""
import copy
import itertools

STATUSES = ("queued", "running", "failed", "done", "canceled")


def seed():
    jobs, seq = {}, itertools.count(1)
    specs = [("compile-api", "failed"), ("compile-ui", "done"),
             ("queue-drain-1", "failed"), ("queue-drain-2", "done"),
             ("run-e2e-nightly", "running"), ("run-load-15m", "queued"),
             ("compile-worker", "failed"), ("run-canary-5pct", "done"),
             ("queue-backfill", "canceled"), ("run-e2e-weekly", "queued"),
             ("compile-docs", "done"), ("run-rollback-drill", "failed")]
    for name, st in specs:
        i = next(seq)
        jobs[i] = {"id": i, "name": name, "status": st, "version": 1, "runs": []}
    incidents = {
        1: {"id": 1, "title": "queue depth spike", "severity": "high",
            "actions": ["paged on-call"]},
        2: {"id": 2, "title": "canary error budget burn", "severity": "high",
            "actions": []},
        3: {"id": 3, "title": "slow compile farm", "severity": "medium",
            "actions": ["opened ticket"]},
        4: {"id": 4, "title": "docs build flake", "severity": "low", "actions": []},
    }
    return {"jobs": jobs, "incidents": incidents, "audit": [],
            "idempotency": {}, "run_seq": itertools.count(1000)}


def snapshot(state):
    return copy.deepcopy(state)
