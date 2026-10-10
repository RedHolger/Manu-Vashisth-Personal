"""Hand-calculated chart tests: known in/out-of-control, nulls, capability."""
import json
import sys
import unittest

sys.path.insert(0, "src")
from charts import batch_stats, capability, limits, load_batches, verdicts

ACTIONS = json.load(open("datasets/actions.json"))


class TestHandCalcs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = load_batches("datasets/batches.csv")
        cls.lim = limits(cls.stats)
        cls.ver = verdicts(cls.stats, cls.lim)

    def test_fixture_counts(self):
        self.assertEqual(len(self.stats), 10)
        self.assertEqual(self.stats["B09"]["nulls"], 3)

    def test_shifted_flagged_clean_clear(self):
        self.assertEqual(self.ver["B07"], ["xbar-beyond-limits"])
        self.assertEqual(self.ver["B08"], ["xbar-beyond-limits"])
        for b in ("B01", "B02", "B03", "B04", "B05", "B06", "B10"):
            self.assertEqual(self.ver[b], [], b)

    def test_null_batch_valid_verdict(self):
        self.assertEqual(self.stats["B09"]["nulls"], 3)
        self.assertEqual(self.ver["B09"], [])

    def test_capability_range(self):
        cpk = capability(self.stats)["cpk"]
        self.assertTrue(1.3 < cpk < 1.7, cpk)

    def test_actions_cover_flagged(self):
        flagged = {b for b, v in self.ver.items() if v}
        acted = {a["batch"] for a in ACTIONS}
        self.assertTrue(flagged <= acted, flagged - acted)

    def test_traceability(self):
        total = sum(s["n"] for s in self.stats.values())
        self.assertEqual(total, 200)
        counted = sum(s["nulls"] for s in self.stats.values())
        valid = sum(len(s["values"]) for s in self.stats.values())
        self.assertEqual(counted + valid, total)


if __name__ == "__main__":
    unittest.main(verbosity=2)
