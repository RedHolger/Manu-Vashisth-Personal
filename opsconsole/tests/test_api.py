"""API tests vs a live in-process server: auth, paging, stale, idempotency, cancel."""
import http.client
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

sys.path.insert(0, "backend")
import adapters
import server


def req(method, path, role="viewer", body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", SRV_PORT, timeout=5)
    h = {"X-Role": role, "Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=data, headers=h)
    r = conn.getresponse()
    out = (r.status, json.loads(r.read().decode() or "{}"))
    conn.close()
    return out


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global SRV_PORT
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.API)
        SRV_PORT = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()

    def setUp(self):
        server.STATE = adapters.seed()

    def test_auth_matrix(self):
        st, _ = req("POST", "/api/jobs/1/retry", role="viewer",
                    headers={"Idempotency-Key": "k", "If-Match": "1"})
        self.assertEqual(st, 403)
        st, _ = req("GET", "/api/audit", role="operator")
        self.assertEqual(st, 403)
        st, body = req("GET", "/api/audit", role="admin")
        self.assertEqual(st, 200)

    def test_pagination(self):
        st, body = req("GET", "/api/jobs?per_page=5&page=2")
        self.assertEqual((st, len(body["items"]), body["total"]), (200, 5, 12))
        st, body = req("GET", "/api/jobs?per_page=500")
        self.assertEqual(body["per_page"], 50)
        st, body = req("GET", "/api/jobs?page=99")
        self.assertEqual(body["items"], [])

    def test_stale_version_409(self):
        st, body = req("POST", "/api/jobs/1/retry", role="operator",
                       headers={"Idempotency-Key": "s1", "If-Match": "999"})
        self.assertEqual(st, 409)
        self.assertEqual(body["current"], 1)

    def test_idempotent_retry(self):
        h = {"Idempotency-Key": "dup-1", "If-Match": "1"}
        st1, b1 = req("POST", "/api/jobs/1/retry", role="operator", headers=h)
        st2, b2 = req("POST", "/api/jobs/1/retry", role="operator", headers=h)
        self.assertEqual((st1, st2), (200, 200))
        self.assertFalse(b1["replayed"])
        self.assertTrue(b2["replayed"])
        self.assertEqual(b1["run_id"], b2["run_id"])
        _, job = req("GET", "/api/jobs/1")
        self.assertEqual(len(job["runs"]), 1)  # one run despite two calls

    def test_retry_rules(self):
        h = {"Idempotency-Key": "m1", "If-Match": "1"}
        st, _ = req("POST", "/api/jobs/2/retry", role="operator", headers=h)
        self.assertEqual(st, 422)  # done, not failed
        st, _ = req("POST", "/api/jobs/1/retry", role="operator",
                    headers={"If-Match": "1"})
        self.assertEqual(st, 400)  # key required

    def test_cancel(self):
        _, job = req("GET", "/api/jobs/6")  # queued
        h = {"Idempotency-Key": "c1", "If-Match": str(job["version"])}
        st, body = req("POST", "/api/jobs/6/cancel", role="operator", headers=h)
        self.assertEqual(st, 200)
        self.assertEqual(body["job"]["status"], "canceled")
        st, _ = req("POST", "/api/jobs/2/cancel", role="operator",
                    headers={"Idempotency-Key": "c2", "If-Match": "1"})
        self.assertEqual(st, 422)
        st, _ = req("POST", "/api/jobs/6/cancel", role="operator",
                    headers={"If-Match": "2"})
        self.assertEqual(st, 400)  # cancel now requires a key too

    def test_cross_job_key_reuse_rejected(self):
        # Audit case: same key on job 1 then job 3 must NOT alias results.
        h1 = {"Idempotency-Key": "same-key", "If-Match": "1"}
        st1, b1 = req("POST", "/api/jobs/1/retry", role="operator", headers=h1)
        self.assertEqual(st1, 200)
        st2, b2 = req("POST", "/api/jobs/3/retry", role="operator", headers=h1)
        self.assertEqual(st2, 409)
        self.assertEqual(b2["used_for"], {"job_id": 1, "action": "retry"})
        _, job3 = req("GET", "/api/jobs/3")
        self.assertEqual((job3["status"], job3["version"], job3["runs"]),
                         ("failed", 1, []))  # untouched

    def test_action_mismatch_rejected(self):
        h = {"Idempotency-Key": "act-1", "If-Match": "1"}
        self.assertEqual(req("POST", "/api/jobs/1/retry", role="operator",
                             headers=h)[0], 200)
        st, body = req("POST", "/api/jobs/1/cancel", role="operator", headers=h)
        self.assertEqual(st, 409)
        self.assertEqual(body["used_for"], {"job_id": 1, "action": "retry"})

    def test_cancel_replay(self):
        h = {"Idempotency-Key": "cancel-1", "If-Match": "1"}
        st1, b1 = req("POST", "/api/jobs/6/cancel", role="operator", headers=h)
        self.assertEqual(st1, 200)
        st2, b2 = req("POST", "/api/jobs/6/cancel", role="operator", headers=h)
        self.assertEqual(st2, 200)  # replay succeeds despite bumped version
        self.assertTrue(b2["replayed"])
        self.assertEqual(b1["job"], b2["job"])
        _, job = req("GET", "/api/jobs/6")
        self.assertEqual(job["version"], 2)  # exactly one mutation
        _, audit = req("GET", "/api/audit", role="admin")
        cancels = [a for a in audit["items"] if "cancel-1" in a["detail"]]
        self.assertEqual(len(cancels), 1)  # exactly one audit entry

    def test_concurrent_retry_single_mutation(self):
        results = []
        barrier = threading.Barrier(10)

        def one():
            barrier.wait()
            results.append(req("POST", "/api/jobs/1/retry", role="operator",
                               headers={"Idempotency-Key": "race-1", "If-Match": "1"}))

        threads = [threading.Thread(target=one) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertTrue(all(st == 200 for st, _ in results))
        run_ids = {b["run_id"] for _, b in results}
        self.assertEqual(len(run_ids), 1)  # all callers see the same run
        _, job = req("GET", "/api/jobs/1")
        self.assertEqual(len(job["runs"]), 1)
        _, audit = req("GET", "/api/audit", role="admin")
        retries = [a for a in audit["items"] if "race-1" in a["detail"]]
        self.assertEqual(len(retries), 1)

    def test_incident_actions_and_audit(self):
        st, _ = req("POST", "/api/incidents/2/actions", role="viewer",
                    body={"text": "x"})
        self.assertEqual(st, 403)
        st, body = req("POST", "/api/incidents/2/actions", role="operator",
                       body={"text": "rolled back canary"})
        self.assertEqual(st, 200)
        self.assertIn("rolled back canary", body["incident"]["actions"])
        st, audit = req("GET", "/api/audit", role="admin")
        self.assertTrue(any(a["action"] == "incident.action" for a in audit["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
