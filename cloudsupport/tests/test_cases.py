"""Case tests: each failure reproduces AND recovery succeeds. Stdlib only."""
import sys
import unittest

sys.path.insert(0, "src")
from cases import CASES


class TestCases(unittest.TestCase):
    def test_dns(self):
        rec = CASES["dns_unresolvable"]()
        self.assertEqual(rec["outcome"], "pass")
        phases = [s["phase"] for s in rec["steps"]]
        for p in ("symptom", "diagnostics", "root_cause", "fix", "recovery_proof",
                  "customer_explanation"):
            self.assertIn(p, phases)

    def test_tcp(self):
        rec = CASES["tcp_refused"]()
        self.assertEqual(rec["outcome"], "pass")
        self.assertIn(b"OK", str(rec["steps"]).encode())

    def test_http(self):
        rec = CASES["http_timeout"]()
        self.assertEqual(rec["outcome"], "pass")

    def test_tls(self):
        rec = CASES["tls_hostname"]()
        self.assertIn(rec["outcome"], ("pass", "skip"))
        if rec["outcome"] == "skip":
            self.assertIn("openssl", rec.get("note", ""))

    def test_upload(self):
        rec = CASES["upload_expiry"]()
        self.assertEqual(rec["outcome"], "pass")

    def test_evidence_shape(self):
        for name, fn in CASES.items():
            rec = fn()
            self.assertIn(rec["outcome"], ("pass", "skip"), name)
            if rec["outcome"] == "pass":
                kinds = {s["phase"] for s in rec["steps"]}
                self.assertTrue({"symptom", "recovery_proof"} <= kinds, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
