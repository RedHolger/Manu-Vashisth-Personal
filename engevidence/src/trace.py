"""Traceability store + matrix/gap analysis. stdlib (sqlite3) only."""
import sqlite3

SCHEMA = """
CREATE TABLE requirements(id TEXT PRIMARY KEY, title TEXT, rev_current TEXT, status TEXT);
CREATE TABLE revisions(req_id TEXT, rev TEXT, note TEXT, live INT,
                       PRIMARY KEY (req_id, rev));
CREATE TABLE tests(id TEXT PRIMARY KEY, req_id TEXT, rev_tested TEXT,
                   result TEXT, evidence TEXT);
CREATE TABLE signoffs(item TEXT PRIMARY KEY, signed INT, note TEXT);
"""

REQS = [
    ("REQ-01", "latch static load", "A", "open"),
    ("REQ-02", "latch corrosion", "A", "open"),
    ("REQ-03", "latch cycle life", "C", "open"),
    ("REQ-04", "bin door sensor", "A", "open"),
    ("REQ-05", "placard legibility", "A", "open"),
    ("REQ-06", "tool-less access", "A", "open"),
    ("REQ-07", "emergency placard contrast", "A", "open"),
]
REVS = [
    ("REQ-01", "A", "initial", 1),
    ("REQ-02", "A", "initial", 1),
    ("REQ-03", "B", "raised cycles to 20k", 1),
    ("REQ-03", "C", "raised cycles to 30k", 1),
    ("REQ-04", "A", "initial", 1),
    ("REQ-05", "A", "initial", 1),
    ("REQ-06", "A", "initial", 1),
    ("REQ-07", "A", "initial", 1),
]
TESTS = [
    ("T-01", "REQ-01", "A", "pass", "ev/T-01.pdf"),
    ("T-02", "REQ-02", "A", "pass", "ev/T-02.pdf"),
    ("T-03a", "REQ-03", "B", "pass", "ev/T-03a.pdf"),
    ("T-03b", "REQ-03", "C", "pending", None),
    ("T-04", "REQ-04", "A", "pass", "ev/T-04.pdf"),
    ("T-05", "REQ-04", "A", "pass", None),
    ("T-06", "REQ-05", "A", "fail", "ev/T-06.pdf"),
    ("T-07", "REQ-06", "A", "pass", "ev/T-07.pdf"),
]


def init_db(path=":memory:"):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO requirements VALUES (?,?,?,?)", REQS)
    db.executemany("INSERT INTO revisions VALUES (?,?,?,?)", REVS)
    db.executemany("INSERT INTO tests VALUES (?,?,?,?,?)", TESTS)
    db.commit()
    return db


def matrix(db):
    """Per-requirement: tests, orphan?, conflict?, incomplete-evidence?"""
    out = []
    for (rid, title, cur) in db.execute("SELECT id, title, rev_current FROM requirements"):
        ts = db.execute("SELECT id, rev_tested, result, evidence FROM tests WHERE req_id=?",
                        (rid,)).fetchall()
        live = [r[0] for r in db.execute(
            "SELECT rev FROM revisions WHERE req_id=? AND live=1", (rid,)).fetchall()]
        out.append({
            "req": rid, "title": title, "rev_current": cur,
            "tests": [{"id": t[0], "rev": t[1], "result": t[2]} for t in ts],
            "orphan": not ts,
            "conflict": sorted(live) if len(live) > 1 else [],
            "incomplete_evidence": [t[0] for t in ts if t[2] == "pass" and not t[3]],
            "pending": [t[0] for t in ts if t[2] == "pending"],
            "failed": [t[0] for t in ts if t[2] == "fail"],
        })
    return out


def gaps(rows):
    return {
        "orphans": [r["req"] for r in rows if r["orphan"]],
        "conflicts": {r["req"]: r["conflict"] for r in rows if r["conflict"]},
        "incomplete_evidence": [t for r in rows for t in r["incomplete_evidence"]],
        "pending": [t for r in rows for t in r["pending"]],
        "failed": [t for r in rows for t in r["failed"]],
    }
