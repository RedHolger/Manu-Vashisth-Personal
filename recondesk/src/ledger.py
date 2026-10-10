"""Invoice/payment reconciliation engine. stdlib (sqlite3, decimal) only."""
import sqlite3
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

AS_OF = date(2026, 10, 8)
RATES = {"EUR": Decimal("1"), "USD": Decimal("0.92"), "GBP": Decimal("1.17")}
TOL = 1  # minor-unit tolerance for FX dust
BUCKETS = [(0, "current"), (30, "1-30"), (60, "31-60"), (90, "61-90"), (10**9, "90+")]


def to_base(amount_minor, ccy):
    return int((Decimal(amount_minor) * RATES[ccy]).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def age_bucket(due_iso):
    days = (AS_OF - date.fromisoformat(due_iso)).days
    for limit, name in BUCKETS:
        if days <= limit:
            return name, days
    raise AssertionError("unreachable")


def init_db(path=":memory:"):
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE invoices(id TEXT PRIMARY KEY, cp TEXT, amount INT, ccy TEXT,
                          due TEXT, status TEXT DEFAULT 'open');
    CREATE TABLE payments(id TEXT PRIMARY KEY, amount INT, ccy TEXT,
                          value_date TEXT, ref TEXT);
    CREATE TABLE allocations(id INTEGER PRIMARY KEY, payment_id TEXT,
                             invoice_id TEXT, amount_base INT, note TEXT);
    """)
    return db


def seed(db, invoices, payments):
    db.executemany("INSERT INTO invoices(id,cp,amount,ccy,due) VALUES (?,?,?,?,?)", invoices)
    db.executemany("INSERT INTO payments(id,amount,ccy,value_date,ref) VALUES (?,?,?,?,?)", payments)
    db.commit()


def reconcile(db):
    """Allocate payments in id order. Returns exceptions list."""
    exceptions = []
    consumed = set()  # (ref, amount, ccy) already used
    open_base = {}
    for r in db.execute("SELECT id, amount, ccy, due FROM invoices"):
        open_base[r[0]] = to_base(r[1], r[2])
    alloc_id = 0
    for pid, amount, ccy, vdate, ref in db.execute(
            "SELECT id, amount, ccy, value_date, ref FROM payments ORDER BY id"):
        inv = db.execute("SELECT id, due FROM invoices WHERE id=?", (ref,)).fetchone()
        if inv is None:
            exceptions.append({"kind": "unmatched", "payment": pid, "ref": ref})
            continue
        if (ref, amount, ccy) in consumed:
            exceptions.append({"kind": "duplicate", "payment": pid, "ref": ref})
            continue
        pay_base = to_base(amount, ccy)
        due_open = open_base[ref]
        if due_open <= 0:
            exceptions.append({"kind": "duplicate", "payment": pid, "ref": ref})
            continue
        applied = min(pay_base, due_open)
        open_base[ref] = due_open - applied
        consumed.add((ref, amount, ccy))
        note = ""
        if 0 < open_base[ref] <= TOL:
            open_base[ref] = 0
            note = "fx-dust-tolerance"
        alloc_id += 1
        db.execute("INSERT INTO allocations(payment_id,invoice_id,amount_base,note) VALUES (?,?,?,?)",
                   (pid, ref, applied, note))
        if pay_base > due_open + TOL:
            exceptions.append({"kind": "overpayment", "payment": pid, "ref": ref,
                               "unapplied_base": pay_base - due_open})
        db.execute("UPDATE invoices SET status=? WHERE id=?",
                   ("matched" if open_base[ref] == 0 else "partial", ref))
    db.commit()
    return exceptions


def report(db, exceptions):
    inv = db.execute("SELECT id, cp, amount, ccy, due, status FROM invoices").fetchall()
    per_ccy, base_invoiced, base_open = {}, 0, 0
    open_rows = []
    for iid, cp, amount, ccy, due, status in inv:
        per_ccy[ccy] = per_ccy.get(ccy, 0) + amount
        b = to_base(amount, ccy)
        base_invoiced += b
        if status != "matched":
            applied = db.execute("SELECT COALESCE(SUM(amount_base),0) FROM allocations WHERE invoice_id=?",
                                 (iid,)).fetchone()[0]
            still = b - applied
            base_open += still
            bucket, days = age_bucket(due)
            open_rows.append({"invoice": iid, "status": status, "open_base": still,
                              "bucket": bucket, "past_due_days": days})
    refs = {p[0] for p in db.execute("SELECT DISTINCT ref FROM payments")}
    known = {r[0] for r in db.execute("SELECT id FROM invoices")}
    matchable = sorted(refs & known)
    matched = db.execute("SELECT COUNT(*) FROM invoices WHERE status='matched'").fetchone()[0]
    return {
        "as_of": AS_OF.isoformat(),
        "invoiced_per_ccy_minor": per_ccy,
        "invoiced_base_minor": base_invoiced,
        "open_base_minor": base_open,
        "match_rate": f"{matched}/{len(matchable)}",
        "exceptions": exceptions,
        "open_rows": open_rows,
        "definitions": "match=same ref within 1 minor unit; FX half-up to EUR base "
                       "(USD 0.92, GBP 1.17); aging vs 2026-10-08; educational, no advice",
    }
