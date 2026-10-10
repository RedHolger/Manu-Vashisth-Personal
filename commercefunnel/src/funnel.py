"""Funnel + fulfilment metrics over a deduped sqlite event store. stdlib only."""
import math
import sqlite3
from datetime import date

SCHEMA = """CREATE TABLE events(user_id TEXT, event TEXT, product TEXT,
             ts TEXT, session TEXT, extra TEXT,
             UNIQUE(session, event, product, ts));"""


def init_db(path=":memory:"):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def ingest(db, rows):
    """Insert rows; exact (session,event,product,ts) replays collapse via a
    UNIQUE constraint, so dedup is persistent across batches. Returns n_deduped."""
    before = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    db.executemany("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?)", rows)
    db.commit()
    after = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return len(rows) - (after - before)


def stage_users(db, event):
    return {r[0] for r in db.execute("SELECT DISTINCT user_id FROM events WHERE event=?", (event,))}


def wilson(x, n, z=1.96):
    if n == 0:
        return [0.0, 1.0]
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - m) / d), 4), round(min(1.0, (c + m) / d), 4)]


def _frac(hit, den, what):
    """Rate with explicit unavailable/null semantics for zero denominators:
    numerator and denominator are always preserved, and the Wilson interval
    keeps its degenerate [0, 1] form (maximal uncertainty, not zero)."""
    if not den:
        return {"rate": f"{hit}/{den}", "frac": None, "ci95": wilson(hit, den),
                "unavailable": f"no {what} users"}
    return {"rate": f"{hit}/{den}", "frac": round(hit / den, 4),
            "ci95": wilson(hit, den)}


def rate(db, num_event, den_event):
    num = stage_users(db, num_event)
    den = stage_users(db, den_event)
    return _frac(len(num & den), len(den), den_event)


def funnel(db):
    v, b, p = (stage_users(db, e) for e in ("view", "basket", "purchase"))
    return {
        "view_basket": _frac(len(v & b), len(v), "viewed"),
        "basket_purchase": _frac(len(b & p), len(b), "basket"),
        "view_purchase": _frac(len(v & p), len(v), "viewed"),
    }


def substitution_rate(db):
    stock = {r[0] for r in db.execute("SELECT DISTINCT user_id FROM events WHERE event='stockout'")}
    acc = {r[0] for r in db.execute("SELECT DISTINCT user_id FROM events WHERE event='substitute'")}
    return _frac(len(stock & acc), len(stock), "stockout")


def ontime_rate(db):
    rows = db.execute("SELECT extra FROM events WHERE event='delivered'").fetchall()
    on = sum(1 for (e,) in rows if e == "on-time")
    return _frac(on, len(rows), "delivered")


def cohorts(db):
    """Weekly acquisition cohorts (Monday of first-seen week) with purchase rate."""
    first = {}
    for u, ts in db.execute("SELECT DISTINCT user_id, ts FROM events"):
        d = date.fromisoformat(ts[:10])
        mon = d.fromordinal(d.toordinal() - d.weekday())
        if u not in first or mon < first[u]:
            first[u] = mon
    buyers = stage_users(db, "purchase")
    groups = {}
    for u, mon in first.items():
        groups.setdefault(str(mon), []).append(u)
    return {m: {"rate": f"{sum(1 for u in us if u in buyers)}/{len(us)}",
                "frac": round(sum(1 for u in us if u in buyers) / len(us), 4)}
            for m, us in sorted(groups.items())}
