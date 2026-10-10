"""Frozen evaluation over all methods. Writes results/measure.json."""
import json
import sys
import time

sys.path.insert(0, "src")
from metrics import bootstrap_ci, ndcg_at_k, recall_at_k, reciprocal_rank
from retrieve import METHODS

SEED = 42
catalog = json.load(open("datasets/catalog.json"))
queries = json.load(open("datasets/queries.json"))
qrels = json.load(open("datasets/qrels.json"))
cold_ids = {q["id"] for q in queries if q["cold"]}

out = {"n_docs": len(catalog), "n_queries": len(queries),
       "n_cold": len(cold_ids), "seed": SEED, "methods": {}}
for name, fn in METHODS.items():
    rec5, rec10, ndcg, mrr, lat, cold5 = [], [], [], [], [], []
    for q in queries:
        t0 = time.perf_counter()
        ranked = fn(q["text"], catalog)
        lat.append((time.perf_counter() - t0) * 1000)
        rel = qrels[q["id"]]
        r5 = recall_at_k(ranked, rel, 5)
        rec5.append(r5)
        rec10.append(recall_at_k(ranked, rel, 10))
        ndcg.append(ndcg_at_k(ranked, rel, 10))
        mrr.append(reciprocal_rank(ranked, rel))
        if q["id"] in cold_ids:
            cold5.append(r5)
    avg = lambda v: round(sum(v) / len(v), 4)
    out["methods"][name] = {
        "recall@5": avg(rec5), "recall@5_ci95": bootstrap_ci(rec5),
        "recall@10": avg(rec10), "ndcg@10": avg(ndcg), "mrr": avg(mrr),
        "mean_latency_ms": round(sum(lat) / len(lat), 3),
        "cold_recall@5": avg(cold5),
    }
json.dump(out, open("results/measure.json", "w"), indent=2)
print(json.dumps(out, indent=2))
