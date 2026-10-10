"""Eval tests: metric hand-checks, frozen contracts, determinism."""
import json
import subprocess
import sys
import unittest

sys.path.insert(0, "src")
from metrics import bootstrap_ci, ndcg_at_k, reciprocal_rank, recall_at_k


class TestMetrics(unittest.TestCase):
    def test_perfect_ranking(self):
        ranked = [("a", 3.0), ("c", 2.0), ("b", 1.0)]
        self.assertEqual(recall_at_k(ranked, ["a", "c"], 5), 1.0)
        self.assertAlmostEqual(ndcg_at_k(ranked, ["a", "c"], 5), 1.0, places=6)
        self.assertEqual(reciprocal_rank(ranked, ["a"]), 1.0)

    def test_partial_ranking(self):
        ranked = [("x", 2.0), ("a", 1.0)]
        self.assertEqual(recall_at_k(ranked, ["a"], 1), 0.0)
        self.assertEqual(reciprocal_rank(ranked, ["a"]), 0.5)
        self.assertEqual(reciprocal_rank(ranked, ["zzz"]), 0.0)

    def test_bootstrap_shape(self):
        lo, hi = bootstrap_ci([1.0, 0.0, 1.0, 0.0])
        self.assertLessEqual(lo, hi)
        self.assertTrue(0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0)


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


class TestFrozen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = load_json("datasets/catalog.json")
        cls.q = load_json("datasets/queries.json")
        cls.qr = load_json("datasets/qrels.json")

    def test_counts(self):
        self.assertEqual(len(self.cat), 60)
        self.assertEqual(len(self.q), 24)
        self.assertEqual(sum(1 for x in self.q if x["cold"]), 6)
        self.assertEqual(set(self.qr), {x["id"] for x in self.q})
        ids = {p["id"] for p in self.cat}
        for qid, rel in self.qr.items():
            self.assertTrue(rel and all(r in ids for r in rel), qid)

    def test_overlap_contracts_hold(self):
        import re
        stop = {"and", "with", "for", "the", "a", "of", "in", "to", "per"}

        def ct(s):
            return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in stop}

        pt = {p["id"]: ct(p["title"] + " " + p["description"]) for p in self.cat}
        for qu in self.q:
            ov = [len(ct(qu["text"]) & pt[r]) for r in self.qr[qu["id"]]]
            if qu["cold"]:
                self.assertTrue(all(o == 0 for o in ov), qu["id"])
            else:
                self.assertTrue(any(o >= 2 for o in ov), qu["id"])


class TestDeterminism(unittest.TestCase):
    def test_measure_twice_identical(self):
        def metrics_only():
            m = load_json("results/measure.json")
            return {k: ({kk: vv for kk, vv in v.items() if kk != "mean_latency_ms"})
                    for k, v in m["methods"].items()}
        a = subprocess.run([sys.executable, "measure.py"], capture_output=True, text=True)
        self.assertEqual(a.returncode, 0, a.stderr[-1500:])
        first = metrics_only()
        b = subprocess.run([sys.executable, "measure.py"], capture_output=True, text=True)
        self.assertEqual(b.returncode, 0)
        # latency excluded: machine noise, not a metric. Everything else exact.
        self.assertEqual(first, metrics_only())

    def test_bounds_and_keys(self):
        m = load_json("results/measure.json")
        self.assertEqual((m["n_docs"], m["n_queries"], m["n_cold"]), (60, 24, 6))
        self.assertEqual(set(m["methods"]), {"lexical", "dense", "hybrid", "rerank"})
        for name, r in m["methods"].items():
            for k in ("recall@5", "recall@10", "ndcg@10", "mrr", "cold_recall@5"):
                self.assertTrue(0.0 <= r[k] <= 1.0, (name, k))
            self.assertGreater(r["mean_latency_ms"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
