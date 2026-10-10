"""DeliveryPlan FastAPI app over an in-memory seeded plan. Demo auth: none
(all endpoints open; the UI labels the demo role). Synthetic data only."""
from fastapi import FastAPI, HTTPException

import plan

app = FastAPI(title="DeliveryPlan (synthetic demo)")
STATE = plan.seed()


@app.get("/tasks")
def tasks():
    return STATE["tasks"]


@app.get("/milestones")
def milestones():
    return STATE["milestones"]


@app.get("/decisions")
def decisions():
    return STATE["decisions"]


@app.get("/raid")
def raid():
    return STATE["raid"]


@app.get("/charter")
def charter():
    return {"objective": "Ship a synthetic payments launch safely",
            "scope_in": ["ledger build", "settlement batch", "drill"],
            "scope_out": ["real money movement", "production access"],
            "note": "Synthetic training-scope demo charter for a fictional launch."}


@app.get("/stakeholders")
def stakeholders():
    return {"Platform": "AO (lead)", "Risk": "BK (reviewer)", "UI": "CM (build)"}


@app.post("/tasks/{tid}/deps")
def add_dep(tid: str, dep: dict):
    d = dep.get("dep")
    if tid not in STATE["tasks"] or d not in STATE["tasks"]:
        raise HTTPException(404, "unknown task")
    STATE["tasks"][tid]["deps"].append(d)
    cyc = plan.find_cycle(STATE["tasks"])
    if cyc:
        STATE["tasks"][tid]["deps"].remove(d)
        raise HTTPException(422, f"cycle rejected: {' -> '.join(cyc)}")
    STATE["log"].append(f"dep {d} -> {tid}")
    return {"ok": True}


@app.post("/tasks/{tid}/shift")
def shift(tid: str, body: dict):
    if tid not in STATE["tasks"]:
        raise HTTPException(404, "unknown task")
    moved = plan.shift_task(STATE, tid, int(body.get("days", 0)))
    STATE["log"].append(f"shift {tid} by {body.get('days', 0)}d")
    return {"moved": moved}


@app.post("/tasks/{tid}/status")
def status(tid: str, body: dict):
    if tid not in STATE["tasks"]:
        raise HTTPException(404, "unknown task")
    if body.get("status") not in ("queued", "in-progress", "done", "blocked"):
        raise HTTPException(400, "bad status")
    STATE["tasks"][tid]["status"] = body["status"]
    return {"ok": True}


@app.post("/decisions")
def decide(body: dict):
    STATE["decisions"].append({"text": body.get("text", "")})
    return {"ok": True, "n": len(STATE["decisions"])}


@app.post("/raid")
def add_raid(body: dict):
    STATE["raid"].append(body)
    return {"ok": True, "n": len(STATE["raid"])}


@app.get("/reports/milestones")
def rep_milestones():
    return {mid: {"drift_days": plan.milestone_drift(STATE, mid),
                  "planned": m["planned"], "prereqs": m["prereqs"]}
            for mid, m in STATE["milestones"].items()}


@app.get("/reports/weekly")
def rep_weekly():
    return plan.weekly_report(STATE)
