"""DeliveryPlan domain: seeded state, graph math, reports. No framework imports."""
from datetime import date

TODAY = date(2026, 10, 8)


def seed():
    tasks = {
        "T1": {"title": "design API", "team": "Platform", "owner": "AO",
               "status": "done", "start": "2026-09-01", "dur": 5, "deps": []},
        "T2": {"title": "build ledger", "team": "Platform", "owner": "AO",
               "status": "in-progress", "start": "2026-09-07", "dur": 8, "deps": ["T1"]},
        "T3": {"title": "risk rules", "team": "Risk", "owner": "BK",
               "status": "queued", "start": "2026-09-07", "dur": 6, "deps": ["T1"]},
        "T4": {"title": "settlement batch", "team": "Platform", "owner": "AO",
               "status": "queued", "start": "2026-09-16", "dur": 4, "deps": ["T2", "T3"]},
        "T5": {"title": "dashboard", "team": "UI", "owner": "CM",
               "status": "queued", "start": "2026-09-16", "dur": 3, "deps": ["T2"]},
        "T7": {"title": "docs", "team": "UI", "owner": "CM",
               "status": "done", "start": "2026-09-01", "dur": 2, "deps": []},
        "T8": {"title": "rollback drill", "team": "Platform", "owner": "AO",
               "status": "queued", "start": "2026-09-21", "dur": 2, "deps": ["T4"]},
    }
    milestones = {
        "M1": {"name": "code freeze", "planned": "2026-09-22",
               "prereqs": ["T4", "T5"], "exit": "T4 and T5 done, drill scheduled"},
    }
    raid = [
        {"id": "R1", "type": "risk", "text": "settlement window overruns",
         "owner": "AO", "rating": "high"},
        {"id": "R2", "type": "assumption", "text": "risk rules API stable",
         "owner": "BK", "rating": "med"},
        {"id": "R3", "type": "issue", "text": "dashboard data lag",
         "owner": "CM", "rating": "med"},
        {"id": "R4", "type": "dependency", "text": "risk team review slot",
         "owner": "BK", "rating": "high"},
    ]
    return {"tasks": tasks, "milestones": milestones, "decisions": [],
            "raid": raid, "log": []}


def end_of(task):
    return date.fromisoformat(task["start"]).toordinal() + task["dur"]


def find_cycle(tasks):
    """Return a cycle path in execution order, or None (DFS on dependencies)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t: WHITE for t in tasks}
    stack = []

    def visit(u):
        color[u] = GRAY
        stack.append(u)
        for v in tasks[u]["deps"]:
            if v not in color:
                continue
            if color[v] == GRAY:
                return stack[stack.index(v):] + [v]
            if color[v] == WHITE:
                hit = visit(v)
                if hit:
                    return hit
        stack.pop()
        color[u] = BLACK
        return None

    for t in tasks:
        if color[t] == WHITE:
            hit = visit(t)
            if hit:
                return list(reversed(hit))  # execution order, not edge order
    return None


def critical_path(tasks):
    """Longest duration path (topological DP). Returns (path, length)."""
    order, seen, temp = [], set(), set()

    def visit(u):
        if u in temp:
            raise ValueError("cycle")
        if u in seen:
            return
        temp.add(u)
        for v in tasks[u]["deps"]:
            visit(v)
        temp.remove(u)
        seen.add(u)
        order.append(u)

    for t in tasks:
        visit(t)
    best = {}
    for u in order:
        if not tasks[u]["deps"]:
            best[u] = (tasks[u]["dur"], [u])
        else:
            pre, path = max(((best[v][0], best[v][1]) for v in tasks[u]["deps"]),
                            key=lambda p: p[0])
            best[u] = (pre + tasks[u]["dur"], path + [u])
    end = max(best, key=lambda u: best[u][0])
    length, path = best[end]
    return path, length


def shift_task(state, tid, days):
    """Shift a task and cascade to dependents (keeps durations). Returns moved ids."""
    tasks = state["tasks"]
    # dependents closure
    moved = []

    def cascade(u, delta):
        t = tasks[u]
        d = date.fromisoformat(t["start"])
        t["start"] = d.fromordinal(d.toordinal() + delta).isoformat()
        moved.append(u)
        for w, tw in tasks.items():
            if u in tw["deps"] and w not in moved:
                # keep dependent starting after prerequisite ends
                need = end_of(t) + 1 - date.fromisoformat(tw["start"]).toordinal()
                if need > 0:
                    cascade(w, need)

    cascade(tid, days)
    return moved


def milestone_drift(state, mid):
    m = state["milestones"][mid]
    proj = max(end_of(state["tasks"][t]) for t in m["prereqs"])
    planned = date.fromisoformat(m["planned"]).toordinal()
    return proj - planned  # negative = buffer remaining


def weekly_report(state):
    by_status = {}
    for t in state["tasks"].values():
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    drifts = {mid: milestone_drift(state, mid) for mid in state["milestones"]}
    risks = [r for r in state["raid"] if r["rating"] == "high" and r["type"] in ("risk", "issue")]
    done = by_status.get("done", 0)
    total = sum(by_status.values())
    nar = (f"Week of {TODAY}: {done}/{total} tasks done; "
           f"milestone drift {drifts}; top open risks: "
           f"{', '.join(r['id'] + ':' + r['text'] for r in risks) or 'none'}.")
    return {"as_of": str(TODAY), "by_status": by_status, "drifts": drifts,
            "top_risks": [r["id"] for r in risks], "narrative": nar}
