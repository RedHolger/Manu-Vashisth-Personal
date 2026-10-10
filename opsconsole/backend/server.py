"""OpsConsole API server (stdlib http.server). Run: python server.py [port].

Idempotency contract (see SPEC.md): a key is scoped to exactly one
(job_id, action) request. Replay is checked FIRST under a lock: a known key
returns its stored immutable response verbatim (no revalidation, no new
mutation, no new audit entry). A known key on a DIFFERENT (job, action) is a
client bug -> 409, never cross-applied. Unknown keys proceed to version/state
validation, then mutate atomically (check/mutate/store/audit under one lock).
"""
import copy
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import adapters

STATE = adapters.seed()
MUTEX = threading.Lock()
ROLES = ("viewer", "operator", "admin")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class API(BaseHTTPRequestHandler):
    server_version = "OpsConsole/1"

    def log_message(self, *a):
        pass

    # -- helpers ---------------------------------------------------------
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _role(self):
        r = self.headers.get("X-Role", "viewer")
        return r if r in ROLES else "viewer"

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw.decode()) if raw else {}

    def _need(self, *allowed):
        if self._role() not in allowed:
            self._send(403, {"error": "forbidden for role " + self._role()})
            return False
        return True

    def _audit(self, actor, action, detail):
        STATE["audit"].append({"t": now(), "actor": actor, "action": action,
                               "detail": detail})

    def _conflict(self, rec):
        return (409, {"error": "key already used for a different request",
                       "used_for": {"job_id": rec["job_id"], "action": rec["action"]}})

    def _replay(self, rec):
        return (200, {**copy.deepcopy(rec["response"]), "replayed": True})

    @staticmethod
    def _version(ver):
        try:
            return int(ver) if ver is not None else None
        except (TypeError, ValueError):
            return "bad"

    def _retry_locked(self, role, jid, key, ver):
        """Entire check/validate/mutate/store runs under MUTEX (caller holds it)."""
        rec = STATE["idempotency"].get(key)
        if rec is not None:
            if (rec["job_id"], rec["action"]) != (jid, "retry"):
                return self._conflict(rec)
            return self._replay(rec)
        job = STATE["jobs"].get(jid)
        if job is None:
            return 404, {"error": "not found"}
        want = self._version(ver)
        if want == "bad" or want != job["version"]:
            return 409, {"error": "stale version", "current": job["version"]}
        if job["status"] != "failed":
            return 422, {"error": "only failed jobs are retryable"}
        run_id = next(STATE["run_seq"])
        job["status"] = "queued"
        job["version"] += 1
        job["runs"].append(run_id)
        self._audit(role, "job.retry", f"job={job['id']} run={run_id} key={key}")
        res = {"job": dict(job), "run_id": run_id, "replayed": False}
        STATE["idempotency"][key] = {
            "job_id": jid, "action": "retry", "response": copy.deepcopy(res)}
        return 200, res

    def _cancel_locked(self, role, jid, key, ver):
        """Entire check/validate/mutate/store runs under MUTEX (caller holds it)."""
        rec = STATE["idempotency"].get(key)
        if rec is not None:
            if (rec["job_id"], rec["action"]) != (jid, "cancel"):
                return self._conflict(rec)
            return self._replay(rec)
        job = STATE["jobs"].get(jid)
        if job is None:
            return 404, {"error": "not found"}
        want = self._version(ver)
        if want == "bad" or want != job["version"]:
            return 409, {"error": "stale version", "current": job["version"]}
        if job["status"] not in ("queued", "running"):
            return 422, {"error": "only queued/running jobs are cancelable"}
        job["status"] = "canceled"
        job["version"] += 1
        self._audit(role, "job.cancel", f"job={job['id']} key={key}")
        res = {"job": dict(job), "replayed": False}
        STATE["idempotency"][key] = {
            "job_id": jid, "action": "cancel", "response": copy.deepcopy(res)}
        return 200, res

    # -- routes ----------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        parts = url.path.strip("/").split("/")
        if parts[:2] == ["api", "jobs"] and len(parts) == 2:
            status = (q.get("status") or [None])[0]
            page = max(1, int(q.get("page", ["1"])[0]))
            per = min(50, max(1, int(q.get("per_page", ["10"])[0])))
            items = [j for j in STATE["jobs"].values()
                     if status is None or j["status"] == status]
            items.sort(key=lambda j: j["id"])
            total = len(items)
            self._send(200, {"items": items[(page - 1) * per:page * per],
                             "page": page, "per_page": per, "total": total})
        elif parts[:2] == ["api", "jobs"] and len(parts) == 3:
            job = STATE["jobs"].get(int(parts[2]))
            self._send(200 if job else 404, job or {"error": "not found"})
        elif parts[:2] == ["api", "incidents"] and len(parts) == 2:
            sev = (q.get("severity") or [None])[0]
            items = [i for i in STATE["incidents"].values()
                     if sev is None or i["severity"] == sev]
            self._send(200, {"items": items})
        elif parts[:2] == ["api", "incidents"] and len(parts) == 3:
            inc = STATE["incidents"].get(int(parts[2]))
            self._send(200 if inc else 404, inc or {"error": "not found"})
        elif parts == ["api", "audit"]:
            if not self._need("admin"):
                return
            self._send(200, {"items": STATE["audit"]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        parts = url.path.strip("/").split("/")
        role = self._role()
        if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "retry":
            if not self._need("operator", "admin"):
                return
            try:
                jid = int(parts[2])
            except ValueError:
                self._send(404, {"error": "not found"})
                return
            job = STATE["jobs"].get(jid)
            if job is None:
                self._send(404, {"error": "not found"})
                return
            key = self.headers.get("Idempotency-Key")
            if not key:
                self._send(400, {"error": "Idempotency-Key required"})
                return
            with MUTEX:
                code, obj = self._retry_locked(role, jid, key,
                                               self.headers.get("If-Match"))
            self._send(code, obj)
        elif len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "cancel":
            if not self._need("operator", "admin"):
                return
            try:
                jid = int(parts[2])
            except ValueError:
                self._send(404, {"error": "not found"})
                return
            job = STATE["jobs"].get(jid)
            if job is None:
                self._send(404, {"error": "not found"})
                return
            key = self.headers.get("Idempotency-Key")
            if not key:
                self._send(400, {"error": "Idempotency-Key required"})
                return
            with MUTEX:
                code, obj = self._cancel_locked(role, jid, key,
                                                self.headers.get("If-Match"))
            self._send(code, obj)
        elif len(parts) == 4 and parts[:2] == ["api", "incidents"] and parts[3] == "actions":
            if not self._need("operator", "admin"):
                return
            inc = STATE["incidents"].get(int(parts[2]))
            if inc is None:
                self._send(404, {"error": "not found"})
                return
            text = self._body().get("text", "")
            if not text:
                self._send(400, {"error": "text required"})
                return
            inc["actions"].append(text)
            self._audit(role, "incident.action", f"incident={inc['id']}: {text[:80]}")
            self._send(200, {"incident": dict(inc)})
        else:
            self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8471
    ThreadingHTTPServer(("127.0.0.1", port), API).serve_forever()
