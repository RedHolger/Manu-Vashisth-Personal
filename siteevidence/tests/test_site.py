"""Seeded-defect + API tests."""
import sys
import unittest

sys.path.insert(0, "backend")
import store  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402


class TestDomain(unittest.TestCase):
    def test_overdue(self):
        self.assertEqual(store.overdue(store.init_db()), ["RFI-1"])

    def test_missing_evidence(self):
        self.assertEqual(store.missing_evidence(store.init_db()), ["INSP-1"])

    def test_mismatch(self):
        self.assertEqual(store.revision_mismatches(store.init_db()),
                         [{"inspection": "INSP-1", "tested": 1, "current": 2}])

    def test_weekly(self):
        w = store.weekly(store.init_db())
        self.assertEqual((w["overdue"], w["failed"]), (["RFI-1"], ["INSP-3"]))
        self.assertEqual(w["open_by_owner"], {"AO": 1, "BK": 1})


class TestAPI(unittest.TestCase):
    def setUp(self):
        api.DB = store.init_db()
        self.c = TestClient(api.app)

    def test_lists(self):
        self.assertEqual(len(self.c.get("/rfis").json()), 3)
        self.assertEqual(len(self.c.get("/inspections").json()), 3)

    def test_weekly_and_handover(self):
        w = self.c.get("/report/weekly").json()
        self.assertEqual(w["overdue"], ["RFI-1"])
        h = self.c.get("/handover").json()
        self.assertIn("SYNTHETIC", h["note"])
        self.assertEqual(len(h["rfis"]), 3)

    def test_mutations_audit(self):
        r = self.c.post("/rfis", json={"id": "RFI-9", "title": "t", "owner": "AO",
                                       "due": "2026-11-01", "actor": "tester"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.post("/rfis", json={"id": "RFI-9", "title": "t",
                                                    "owner": "AO", "due": "2026-11-01"}).status_code, 409)
        self.c.post("/rfis/RFI-9/close", json={"actor": "tester"})
        n = api.DB.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        self.assertGreaterEqual(n, 2)

    def test_inspection_validation(self):
        bad = self.c.post("/inspections", json={"rfi_id": "RFI-9", "result": "pass"})
        self.assertEqual(bad.status_code, 404)
        bad2 = self.c.post("/inspections", json={"rfi_id": "RFI-2", "result": "maybe"})
        self.assertEqual(bad2.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
