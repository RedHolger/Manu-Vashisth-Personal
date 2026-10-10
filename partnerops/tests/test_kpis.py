"""Hand-calculated KPI tests vs local PostgreSQL. Run via ../pg.sh."""
import os
import sys
import unittest

sys.path.insert(0, ".")
os.environ.setdefault("PARTNEROPS_DSN", "dbname=partnerops host=127.0.0.1 port=55434")

import psycopg  # noqa: E402
import kpi  # noqa: E402

DSN = os.environ["PARTNEROPS_DSN"]


def fresh_db():
    with psycopg.connect(DSN, autocommit=True) as db:
        db.execute("DROP TABLE IF EXISTS enablement, deals, partners")
        db.execute(open("sql/schema.sql").read())
        db.execute(open("sql/seed.sql").read())


class TestHandCalcs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_db()

    def test_win_rate(self):
        k = kpi.compute()
        self.assertEqual(k["win_rate"], "5/7")
        self.assertAlmostEqual(k["win_rate_pct"], 71.43, places=2)

    def test_avg_and_outlier(self):
        k = kpi.compute()
        self.assertEqual(k["avg_won_size"], 11666.67)
        self.assertEqual(k["avg_basis"], "3 deals")
        self.assertEqual(k["outliers"]["count"], 1)

    def test_missing_unknown_duplicates(self):
        k = kpi.compute()
        self.assertEqual(k["missing_amount"], 2)
        self.assertEqual(k["unknown_stage"], ["D10"])
        self.assertEqual(k["duplicates"], 1)

    def test_enablement(self):
        k = kpi.compute()
        self.assertEqual(k["enablement"], "3/5")

    def test_narrative_reconciles(self):
        k = kpi.compute()
        n = kpi.narrative(k)
        for token in ("5/7", "11666.67", "3/5", "deduped"):
            self.assertIn(token, n)

    def test_deterministic(self):
        self.assertEqual(kpi.compute(), kpi.compute())


if __name__ == "__main__":
    unittest.main(verbosity=2)
