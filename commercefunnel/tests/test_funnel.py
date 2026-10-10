"""Hand-calculated funnel tests. All numbers from SPEC.md."""
import json
import sys
import unittest

sys.path.insert(0, "src")
from funnel import cohorts, funnel, ingest, init_db, ontime_rate, substitution_rate


def load_rows():
    with open("datasets/events.json") as fh:
        return [tuple(r) for r in json.load(fh)]


def fixture_db():
    db = init_db()
    rows = load_rows()
    dups = ingest(db, rows)
    return db, dups, len(rows)


class TestHandCalcs(unittest.TestCase):
    def test_dedup(self):
        _, dups, n = fixture_db()
        self.assertEqual((dups, n), (1, 26))

    def test_funnel(self):
        db, _, _ = fixture_db()
        f = funnel(db)
        self.assertEqual(f["view_basket"]["rate"], "5/7")
        self.assertEqual(f["basket_purchase"]["rate"], "4/5")
        self.assertEqual(f["view_purchase"]["rate"], "5/7")
        for k in f:
            lo, hi = f[k]["ci95"]
            self.assertLessEqual(lo, hi)

    def test_substitution_and_slots(self):
        db, _, _ = fixture_db()
        self.assertEqual(substitution_rate(db)["rate"], "1/1")
        self.assertEqual(ontime_rate(db)["rate"], "2/3")

    def test_cohorts(self):
        db, _, _ = fixture_db()
        c = cohorts(db)
        self.assertEqual(c["2026-09-07"]["rate"], "4/5")
        self.assertEqual(c["2026-09-14"]["rate"], "1/2")

    def test_idempotent_ingest(self):
        db = init_db()
        rows = load_rows()
        self.assertEqual(ingest(db, rows), 1)
        self.assertEqual(ingest(db, rows), len(rows))  # full replay = all dups

    def test_empty_store_no_crash(self):
        from funnel import funnel as funnel_fn, substitution_rate as sub, ontime_rate as ot
        db = init_db()
        f = funnel_fn(db)
        for step in ("view_basket", "basket_purchase", "view_purchase"):
            self.assertIsNone(f[step]["frac"])
            self.assertIn("unavailable", f[step])
            self.assertEqual(f[step]["ci95"], [0.0, 1.0])  # maximal uncertainty
        self.assertIsNone(sub(db)["frac"])
        self.assertIsNone(ot(db)["frac"])

    def test_view_only_store(self):
        from funnel import funnel as funnel_fn
        db = init_db()
        ingest(db, [("U1", "view", "A", "2026-09-08", "s1", ""),
                    ("U2", "view", "A", "2026-09-09", "s2", "")])
        f = funnel_fn(db)
        self.assertEqual(f["view_basket"]["rate"], "0/2")
        self.assertIsNone(f["basket_purchase"]["frac"])  # zero baskets: explicit null
        self.assertIn("basket", f["basket_purchase"]["unavailable"])

    def test_basket_only_store(self):
        from funnel import funnel as funnel_fn
        db = init_db()
        ingest(db, [("U1", "basket", "A", "2026-09-08", "s1", "")])
        f = funnel_fn(db)
        self.assertIsNone(f["view_basket"]["frac"])  # zero viewers
        self.assertIsNone(f["view_purchase"]["frac"])
        self.assertEqual(f["basket_purchase"]["frac"], 0.0)  # 0/1 is defined


if __name__ == "__main__":
    unittest.main(verbosity=2)
