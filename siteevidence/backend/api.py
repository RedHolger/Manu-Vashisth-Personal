"""SiteEvidence FastAPI app (in-memory seeded store). Synthetic demo data."""
from fastapi import FastAPI, HTTPException

import store as domain

app = FastAPI(title="SiteEvidence (synthetic demo)")
DB = domain.init_db()


def audit(actor, action, detail):
    DB.execute("INSERT INTO audit(actor,action,detail) VALUES (?,?,?)", (actor, action, detail))
    DB.commit()


@app.get("/rfis")
def rfis():
    return domain.handover(DB)["rfis"]


@app.get("/inspections")
def inspections():
    return domain.handover(DB)["inspections"]


@app.get("/report/weekly")
def report():
    return domain.weekly(DB)


@app.get("/handover")
def handover():
    return domain.handover(DB)


@app.post("/rfis")
def add_rfi(body: dict):
    for k in ("id", "title", "owner", "due"):
        if not body.get(k):
            raise HTTPException(400, f"{k} required")
    try:
        DB.execute("INSERT INTO rfis VALUES (?,?,?,?,?,?)",
                   (body["id"], body["title"], body["owner"], body["due"], "open", 1))
        DB.execute("INSERT INTO revisions VALUES (?,?,?)", (body["id"], 1, "initial"))
        DB.commit()
    except Exception:
        raise HTTPException(409, "duplicate rfi id")
    audit(body.get("actor", "demo"), "rfi.add", body["id"])
    return {"ok": True}


@app.post("/inspections")
def add_inspection(body: dict):
    rfi = DB.execute("SELECT rev_current FROM rfis WHERE id=?", (body.get("rfi_id"),)).fetchone()
    if rfi is None:
        raise HTTPException(404, "unknown rfi")
    if body.get("result") not in ("pass", "fail"):
        raise HTTPException(400, "result must pass/fail")
    iid = f"INSP-{body['rfi_id'].split('-')[1]}-{body.get('rev_tested', rfi[0])}"
    DB.execute("INSERT INTO inspections VALUES (?,?,?,?,?,?)",
               (iid, body["rfi_id"], body.get("rev_tested", rfi[0]),
                body.get("date", str(domain.TODAY)), body["result"], body.get("evidence")))
    DB.commit()
    audit(body.get("actor", "demo"), "inspection.add", iid)
    return {"ok": True, "id": iid}


@app.post("/rfis/{rid}/close")
def close(rid: str, body: dict):
    cur = DB.execute("SELECT id FROM rfis WHERE id=?", (rid,)).fetchone()
    if cur is None:
        raise HTTPException(404, "unknown rfi")
    DB.execute("UPDATE rfis SET status='closed' WHERE id=?", (rid,))
    DB.commit()
    audit(body.get("actor", "demo"), "rfi.close", rid)
    return {"ok": True}
