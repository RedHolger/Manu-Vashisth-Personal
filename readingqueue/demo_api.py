"""End-to-end API demo (stdlib urllib). Backend+PG started by demo.sh."""
import json
import sys
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8581"
BASE = f"http://127.0.0.1:{PORT}"
transcript = []


def call(method, path, user="alice", body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-User": user, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            out = (r.status, json.loads(r.read().decode() or "{}"))
    except urllib.error.HTTPError as e:
        out = (e.code, json.loads(e.read().decode() or "{}"))
    transcript.append({"op": f"{method} {path} as {user}", "status": out[0], "body": out[1]})
    return out


st, created = call("POST", "/api/items", body={"title": "Promo standards", "url": "http://x"})
assert st == 201, (st, created)
item_id = created["id"]
st, found = call("GET", f"/api/items?search=promo")
assert st == 200 and found["total"] >= 1
st, _ = call("PATCH", f"/api/items/{item_id}", user="bob", body={"status": "done"})
assert st == 403, st  # not bob's item
st, moved = call("POST", f"/api/items/{item_id}/transfer", body={"to": "bob"})
assert st == 200 and moved["owner"] == "bob", (st, moved)
st, check = call("GET", f"/api/items/{item_id}", user="bob")
assert st == 200 and check["owner"] == "bob"

json.dump(transcript, open("results/demo.json", "w"), indent=2)
print("demo ok:", [(o["op"], o["status"]) for o in transcript])
