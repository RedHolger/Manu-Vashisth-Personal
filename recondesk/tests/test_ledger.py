"""Hand-calculated ledger fixtures + engine tests. All numbers from SPEC.md."""
import json
import sys
import unittest

sys.path.insert(0, "src")
from ledger import age_bucket, init_db, reconcile, report, seed, to_base

_FX = json.load(open("datasets/fixtures.json"))
INV = [tuple(r) for r in _FX["invoices"]]
PAY = [tuple(r) for r in _FX["payments"]]


def fixture_db():
    db = init_db()
    seed(db, INV, PAY)
    return db


class TestHandCalcs(unittest.TestCase):
    def test_fx_half_up(self):
        self.assertEqual(to_base(3333, "GBP"), 3900)   # 3899.61 -> 3900
        self.assertEqual(to_base(2000, "GBP"), 2340)
        self.assertEqual(to_base(5000, "USD"), 4600)
        self.assertEqual(to_base(1, "USD"), 1)          # 0.92 -> half-up 1

    def test_aging_buckets(self):
        self.assertEqual(age_bucket("2026-09-20"), ("1-30", 18))
        self.assertEqual(age_bucket("2026-07-01"), ("90+", 99))
        self.assertEqual(age_bucket("2026-10-08"), ("current", 0))

    def test_reconcile_matches_spec(self):
        db = fixture_db()
        exc = reconcile(db)
        kinds = sorted(e["kind"] for e in exc)
        self.assertEqual(kinds, ["duplicate", "unmatched"])
        st = dict(db.execute("SELECT id, status FROM invoices").fetchall())
        self.assertEqual(st, {"INV-01": "matched", "INV-02": "matched",
                             "INV-03": "partial", "INV-04": "open"})

    def test_report_ties_out(self):
        db = fixture_db()
        exc = reconcile(db)
        rep = report(db, exc)
        self.assertEqual(rep["match_rate"], "2/3")
        self.assertEqual(rep["open_base_minor"], 9060)
        self.assertEqual(rep["invoiced_base_minor"], 10000 + 4600 + 3900 + 7500)
        buckets = {r["invoice"]: r["bucket"] for r in rep["open_rows"]}
        self.assertEqual(buckets, {"INV-03": "90+", "INV-04": "1-30"})
        # every allocated cent accounted: invoiced = open + allocated
        alloc = db.execute("SELECT COALESCE(SUM(amount_base),0) FROM allocations").fetchone()[0]
        self.assertEqual(rep["invoiced_base_minor"], rep["open_base_minor"] + alloc)

    def test_tolerance_dust(self):
        db = init_db()
        seed(db, [("I1", "A", 4600, "EUR", "2026-09-01")],
             [("P1", 4599, "EUR", "2026-09-02", "I1")])
        reconcile(db)
        self.assertEqual(db.execute("SELECT status FROM invoices WHERE id='I1'").fetchone()[0],
                         "matched")

    def test_overpayment_flagged(self):
        db = init_db()
        seed(db, [("I1", "A", 1000, "EUR", "2026-09-01")],
             [("P1", 1500, "EUR", "2026-09-02", "I1")])
        exc = reconcile(db)
        self.assertEqual([e["kind"] for e in exc], ["overpayment"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
