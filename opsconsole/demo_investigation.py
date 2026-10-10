"""Demo an investigation through the same API the UI uses. Starts a fresh server
subprocess, runs investigate -> retry -> verify + incident action, saves
results/demo.json. Exit 1 if any step deviates."""
import http.client
import json
import subprocess
import sys
import time
import urllib.request

PORT = 8479
BASE = f"http://127.0.0.1:{PORT}"
transcript = []


def call(method, path, role="viewer", body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    h = {"X-Role": role, "Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=data, headers=h)
    r = conn.getresponse()
    out = (r.status, json.loads(r.read().decode() or "{}"))
    conn.close()
    transcript.append({"op": f"{method} {path} as {role}", "status": out[0],
                       "body": out[1]})
    return out


srv = subprocess.Popen([sys.executable, "backend/server.py", str(PORT)])
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/jobs", timeout=1).read()
            break
        except OSError:
            time.sleep(0.1)
    # 1. investigate: list failed jobs
    st, failed = call("GET", "/api/jobs?status=failed", role="operator")
    assert st == 200 and failed["total"] >= 1
    job = failed["items"][0]
    # 2. inspect detail
    st, detail = call("GET", f"/api/jobs/{job['id']}", role="operator")
    assert st == 200
    # 3. retry idempotently (same key twice -> one run)
    hdr = {"Idempotency-Key": "demo-investigation-1", "If-Match": str(detail["version"])}
    st1, r1 = call("POST", f"/api/jobs/{job['id']}/retry", role="operator", headers=hdr)
    st2, r2 = call("POST", f"/api/jobs/{job['id']}/retry", role="operator", headers=hdr)
    assert (st1, st2) == (200, 200) and r1["run_id"] == r2["run_id"] and r2["replayed"]
    # 4. verify via audit (admin) + incident action
    st, audit = call("GET", "/api/audit", role="admin")
    assert st == 200 and any(a["action"] == "job.retry" for a in audit["items"])
    st, inc = call("POST", "/api/incidents/1/actions", role="operator",
                   body={"text": "retried failed job from investigation"})
    assert st == 200
    # 5. viewer cannot mutate (403 proof)
    st, _ = call("POST", f"/api/jobs/{job['id']}/cancel", role="viewer",
                 headers={"If-Match": "1"})
    assert st == 403
finally:
    srv.terminate()
    srv.wait(timeout=10)

json.dump(transcript, open("results/demo.json", "w"), indent=2)
print(f"demo ok: {len(transcript)} ops, failed job {job['id']} retried as run {r1['run_id']}")
