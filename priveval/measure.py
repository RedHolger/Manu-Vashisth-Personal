"""Frozen-set evaluation: baseline vs controls. Writes results/measure.json."""
import json
import math
import sys

sys.path.insert(0, "src")
import answer
import store
from answer import unauthorized_canaries


def wilson(x, n, z=1.96):
    if n == 0:
        return [0.0, 1.0]
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - m) / d), 4), round(min(1.0, (c + m) / d), 4)]


def run_mode(mode):
    db = store.init_db()
    attacks = json.load(open("datasets/attacks.json"))
    benign = json.load(open("datasets/benign.json"))
    leaks, successes, util = 0, 0, 0
    attack_rows = []
    for a in attacks:
        r = answer.answer(db, mode, a["user"], a["tenant"], a["query"])
        bad = unauthorized_canaries(r["answer"], a["tenant"])
        executed = [t for t in r["tools"] if t["verdict"] == "executed"]
        hit = bool(bad) or bool(executed)
        leaks += 1 if bad else 0
        successes += 1 if hit else 0
        attack_rows.append({"id": a["id"], "leak": bad, "tools": r["tools"],
                            "abstained": r["answer"] == answer.ABSTAIN})
    for b in benign:
        r = answer.answer(db, mode, b["user"], b["tenant"], b["query"])
        if b["expect"] in r["answer"]:
            util += 1
    # stale: v1 retrievable?
    vis_ids = {c["id"] for c in store.visible_chunks(db, mode, "alice", "alpha")}
    v1 = db.execute("SELECT id FROM chunks WHERE doc_id='refund-policy' AND version=1").fetchone()[0]
    stale_served = v1 in vis_ids
    a11 = answer.answer(db, mode, "alice", "alpha", "refunds within how many days")
    return {
        "leakage": f"{leaks}/{len(attacks)}", "leak_ci95": wilson(leaks, len(attacks)),
        "attack_success": f"{successes}/{len(attacks)}",
        "success_ci95": wilson(successes, len(attacks)),
        "benign_utility": f"{util}/{len(benign)}",
        "stale_v1_visible": stale_served,
        "controls_refund_answer_ok": ("30 days" in a11["answer"]) if mode == "controls" else None,
        "attack_rows": attack_rows,
    }


out = {"baseline": run_mode("baseline"), "controls": run_mode("controls")}

# revocation on a fresh db: revoke bob->beta, bob's benign query must block (controls)
db = store.init_db()
store.revoke_access(db, "bob", "beta")
r_ctl = answer.answer(db, "controls", "bob", "beta", "deploy restart")
r_base = answer.answer(db, "baseline", "bob", "beta", "deploy restart")
out["revocation"] = {
    "controls_blocked": r_ctl["answer"] == answer.ABSTAIN,
    "baseline_blocked": r_base["answer"] == answer.ABSTAIN,  # expected False: no auth
}

# stale-cache scenario on a fresh db: cache v2, then revoke it mid-run.
# Naive cache serves the revoked text (stale); validated cache blocks.
from cache import ChunkCache  # noqa: E402

sc = {}
for mode, policy in (("baseline", "naive"), ("controls", "validated")):
    d2 = store.init_db()
    v2 = d2.execute("SELECT id FROM chunks WHERE doc_id='refund-policy' AND version=2"
                    ).fetchone()[0]
    cache = ChunkCache(policy)
    text1, first = cache.read(d2, v2)
    d2.execute("UPDATE chunks SET revoked=1 WHERE id=?", (v2,))
    d2.commit()
    text2, second = cache.read(d2, v2)
    sc[mode] = {"first": first, "second": second,
                "served_revoked_text": second == "stale-served",
                "stats": cache.stats}
out["stale_cache"] = sc
json.dump(out, open("results/measure.json", "w"), indent=2)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "attack_rows"}
                  for k, v in out.items() if k != "revocation"}, indent=2))
print("revocation:", json.dumps(out["revocation"]))
