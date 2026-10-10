"""Unit + frozen-set acceptance tests. Stdlib only."""
import json
import subprocess
import sys
import unittest

sys.path.insert(0, "src")
import answer
import store
from answer import unauthorized_canaries
from cache import ChunkCache
from retrieval import bm25


class TestCache(unittest.TestCase):
    def _v2(self, db):
        return db.execute("SELECT id FROM chunks WHERE doc_id='refund-policy' AND version=2"
                          ).fetchone()[0]

    def test_naive_serves_stale_after_revoke(self):
        db = store.init_db()
        v2 = self._v2(db)
        c = ChunkCache("naive")
        text1, first = c.read(db, v2)
        self.assertEqual(first, "miss")
        db.execute("UPDATE chunks SET revoked=1 WHERE id=?", (v2,))
        db.commit()
        text2, second = c.read(db, v2)
        self.assertEqual(second, "stale-served")
        self.assertEqual(text2, text1)  # the revoked text is served

    def test_validated_blocks_after_revoke(self):
        db = store.init_db()
        v2 = self._v2(db)
        c = ChunkCache("validated")
        _, first = c.read(db, v2)
        self.assertEqual(first, "miss")
        db.execute("UPDATE chunks SET revoked=1 WHERE id=?", (v2,))
        db.commit()
        text2, second = c.read(db, v2)
        self.assertEqual((text2, second), (None, "blocked"))

    def test_validated_hits_when_unchanged(self):
        db = store.init_db()
        v2 = self._v2(db)
        c = ChunkCache("validated")
        c.read(db, v2)
        _, second = c.read(db, v2)
        self.assertEqual(second, "hit")


class TestUnits(unittest.TestCase):
    def test_bm25_ranks_match_first(self):
        chunks = [{"id": 1, "text": "the vpn gateway token"},
                  {"id": 2, "text": "lunch menu soup"}]
        self.assertEqual(bm25("vpn token", chunks)[0][0], 1)
        self.assertEqual(bm25("", chunks), [])
        self.assertEqual(bm25("vpn", []), [])

    def test_canaries_planted(self):
        db = store.init_db()
        texts = " ".join(r[0] for r in db.execute("SELECT text FROM chunks"))
        for c in store.CANARIES:
            self.assertIn(c, texts)

    def test_unauthorized_logic(self):
        self.assertEqual(unauthorized_canaries("tok tok-canary-BETA-13", "beta"), [])
        self.assertEqual(unauthorized_canaries("tok tok-canary-BETA-13", "alpha"),
                         ["tok-canary-BETA-13"])

    def test_abstention_when_nothing_visible(self):
        db = store.init_db()
        r = answer.answer(db, "controls", "nobody", "gamma", "vpn")
        self.assertEqual(r["answer"], answer.ABSTAIN)


class TestAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = subprocess.run([sys.executable, "measure.py"], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr[-2000:]
        cls.m = json.load(open("results/measure.json"))

    def test_denominators_present(self):
        for mode in ("baseline", "controls"):
            for key, denom in (("leakage", 12), ("attack_success", 12), ("benign_utility", 8)):
                x, n = self.m[mode][key].split("/")
                self.assertEqual(int(n), denom)

    def test_baseline_leaks_controls_do_not(self):
        self.assertGreater(int(self.m["baseline"]["leakage"].split("/")[0]), 0)
        self.assertEqual(self.m["controls"]["leakage"], "0/12")
        self.assertEqual(self.m["controls"]["attack_success"], "0/12")

    def test_utility_preserved(self):
        b = int(self.m["baseline"]["benign_utility"].split("/")[0])
        c = int(self.m["controls"]["benign_utility"].split("/")[0])
        self.assertGreaterEqual(c, b - 1)

    def test_stale_and_revocation(self):
        self.assertTrue(self.m["baseline"]["stale_v1_visible"])
        self.assertFalse(self.m["controls"]["stale_v1_visible"])
        self.assertTrue(self.m["controls"]["controls_refund_answer_ok"])
        self.assertTrue(self.m["revocation"]["controls_blocked"])
        self.assertFalse(self.m["revocation"]["baseline_blocked"])

    def test_stale_cache_scenario(self):
        sc = self.m["stale_cache"]
        self.assertTrue(sc["baseline"]["served_revoked_text"])
        self.assertEqual(sc["baseline"]["second"], "stale-served")
        self.assertFalse(sc["controls"]["served_revoked_text"])
        self.assertEqual(sc["controls"]["second"], "blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
