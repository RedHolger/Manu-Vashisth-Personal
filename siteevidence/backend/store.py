"""SiteEvidence domain + store. sqlite, frozen TODAY. No framework imports."""
import sqlite3
from datetime import date

TODAY = date(2026, 10, 8)

SCHEMA = """
CREATE TABLE rfis(id TEXT PRIMARY KEY, title TEXT, owner TEXT, due TEXT,
                  status TEXT, rev_current INT);
CREATE TABLE revisions(rfi_id TEXT, rev INT, note TEXT,
                       PRIMARY KEY (rfi_id, rev));
CREATE TABLE inspections(id TEXT PRIMARY KEY, rfi_id TEXT, rev_tested INT,
                         on_date TEXT, result TEXT, evidence TEXT);
CREATE TABLE audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, detail TEXT);
"""

SEED_RFIS = [
    ("RFI-1", "parapet flashing", "AO", "2026-09-20", "open", 2),
    ("RFI-2", "expansion joint", "BK", "2026-10-15", "open", 1),
    ("RFI-3", "sealant spec", "CM", "2026-09-25", "answered", 1),
]
SEED_REVS = [
    ("RFI-1", 1, "initial"), ("RFI-1", 2, "added flashing gauge"),
    ("RFI-2", 1, "initial"), ("RFI-3", 1, "initial"),
]
SEED_INSP = [
    ("INSP-1", "RFI-1", 1, "2026-09-22", "pass", None),
    ("INSP-2", "RFI-2", 1, "2026-09-23", "pass", "photo-221"),
    ("INSP-3", "RFI-3", 1, "2026-09-26", "fail", "photo-222"),
]


def init_db(path=":memory:"):
    # check_same_thread=False: tests serve requests from a portal thread.
    # Single-threaded demo/test use only; documented, not a concurrency claim.
    db = sqlite3.connect(path, check_same_thread=False)
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO rfis VALUES (?,?,?,?,?,?)", SEED_RFIS)
    db.executemany("INSERT INTO revisions VALUES (?,?,?)", SEED_REVS)
    db.executemany("INSERT INTO inspections VALUES (?,?,?,?,?,?)", SEED_INSP)
    db.commit()
    return db


def overdue(db):
    return [r[0] for r in db.execute(
        "SELECT id FROM rfis WHERE status='open' AND due < ?", (str(TODAY),)).fetchall()]


def missing_evidence(db):
    return [r[0] for r in db.execute(
        "SELECT id FROM inspections WHERE result='pass' AND evidence IS NULL").fetchall()]


def revision_mismatches(db):
    out = []
    for iid, rid, rev in db.execute("SELECT id, rfi_id, rev_tested FROM inspections"):
        cur = db.execute("SELECT rev_current FROM rfis WHERE id=?", (rid,)).fetchone()[0]
        if rev != cur:
            out.append({"inspection": iid, "tested": rev, "current": cur})
    return out


def weekly(db):
    return {
        "as_of": str(TODAY),
        "as_of": str(TODAY),
        "overdue": overdue(db),
        "missing_evidence": missing_evidence(db),
        "mismatches": revision_mismatches(db),
        "failed": [r[0] for r in db.execute(
            "SELECT id FROM inspections WHERE result='fail'").fetchall()],
        "open_by_owner": dict(db.execute(
            "SELECT owner, COUNT(*) FROM rfis WHERE status='open' GROUP BY owner").fetchall()),
    }


def handover(db):
    rfis = [dict(zip(["id", "title", "owner", "due", "status", "rev"], r))
            for r in db.execute("SELECT * FROM rfis")]
    insp = [dict(zip(["id", "rfi", "rev", "date", "result", "evidence"], r))
            for r in db.execute("SELECT * FROM inspections")]
    return {"rfis": rfis, "inspections": insp, "gaps": weekly(db),
            "note": "SYNTHETIC handover pack for a fictional site. Not a real "
                    "handover; no site competence implied."}
