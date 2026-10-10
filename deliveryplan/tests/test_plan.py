"""Domain + API tests with hand-calculated expectations."""
import sys
import unittest

sys.path.insert(0, "backend")
import plan  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402


class TestGraph(unittest.TestCase):
    def test_no_cycle_in_seed(self):
        self.assertIsNone(plan.find_cycle(plan.seed()["tasks"]))

    def test_cycle_found(self):
        t = plan.seed()["tasks"]
        t["T1"]["deps"].append("T8")
        self.assertEqual(plan.find_cycle(t), ["T1", "T2", "T4", "T8", "T1"])

    def test_critical_path(self):
        path, length = plan.critical_path(plan.seed()["tasks"])
        self.assertEqual((path, length), (["T1", "T2", "T4", "T8"], 19))

    def test_drift_and_shift(self):
        s = plan.seed()
        self.assertEqual(plan.milestone_drift(s, "M1"), -2)
        moved = plan.shift_task(s, "T2", 3)
        self.assertEqual(sorted(moved), ["T2", "T4", "T5", "T8"])
        self.assertEqual(plan.milestone_drift(s, "M1"), 1)

    def test_weekly_traceable(self):
        s = plan.seed()
        rep = plan.weekly_report(s)
        self.assertEqual(rep["by_status"], {"done": 2, "in-progress": 1, "queued": 4})
        self.assertIn("2/7 tasks done", rep["narrative"])


class TestAPI(unittest.TestCase):
    def setUp(self):
        api.STATE = plan.seed()
        self.c = TestClient(api.app)

    def test_cycle_rejected(self):
        r = self.c.post("/tasks/T1/deps", json={"dep": "T8"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("T1 -> T2 -> T4 -> T8 -> T1", r.json()["detail"])

    def test_shift_and_report(self):
        self.assertEqual(self.c.post("/tasks/T2/shift", json={"days": 3}).status_code, 200)
        rep = self.c.get("/reports/milestones").json()
        self.assertEqual(rep["M1"]["drift_days"], 1)

    def test_weekly_matches_state(self):
        rep = self.c.get("/reports/weekly").json()
        tasks = self.c.get("/tasks").json()
        total = sum(rep["by_status"].values())
        self.assertEqual(total, len(tasks))
        self.assertIn(f"{rep['by_status'].get('done', 0)}/{total} tasks done", rep["narrative"])

    def test_charter_and_stakeholders(self):
        self.assertIn("synthetic", self.c.get("/charter").json()["note"].lower())
        self.assertEqual(self.c.get("/stakeholders").json()["Platform"], "AO (lead)")

    def test_decision_and_raid_logs(self):
        self.assertEqual(self.c.post("/decisions", json={"text": "freeze scope"}).json()["n"], 1)
        self.assertEqual(self.c.post("/raid", json={"id": "R5", "type": "risk"}).json()["n"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
