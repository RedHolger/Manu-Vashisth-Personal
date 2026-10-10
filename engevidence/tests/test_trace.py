"""Seeded-defect tests: orphan, conflict, incomplete evidence, package."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, "src")
from trace import gaps, init_db, matrix


class TestSeededDefects(unittest.TestCase):
    def test_orphan(self):
        g = gaps(matrix(init_db()))
        self.assertEqual(g["orphans"], ["REQ-07"])

    def test_conflict(self):
        g = gaps(matrix(init_db()))
        self.assertEqual(g["conflicts"], {"REQ-03": ["B", "C"]})

    def test_incomplete_evidence(self):
        g = gaps(matrix(init_db()))
        self.assertEqual(g["incomplete_evidence"], ["T-05"])

    def test_pending_and_failed(self):
        g = gaps(matrix(init_db()))
        self.assertEqual(g["pending"], ["T-03b"])
        self.assertEqual(g["failed"], ["T-06"])

    def test_matrix_complete(self):
        rows = matrix(init_db())
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(r["tests"] or r["orphan"] for r in rows))


class TestPackage(unittest.TestCase):
    def test_pdf_builds(self):
        p = subprocess.run([sys.executable, "review_package.py"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout[-1500:] + p.stderr[-500:])
        self.assertTrue(os.path.getsize("results/review.pdf") > 1000)
        import json
        pkg = json.load(open("results/review.json"))
        self.assertIn("FICTIONAL", pkg["subject"])
        self.assertFalse(all(s["ready"] for s in pkg["signoff"]))  # gaps exist


if __name__ == "__main__":
    unittest.main(verbosity=2)
