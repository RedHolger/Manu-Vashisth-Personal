"""recall@k, NDCG@k, MRR + bootstrap CI. Binary relevance from qrels."""
import math
import random


def recall_at_k(ranked, rel, k):
    got = {cid for cid, _ in ranked[:k]} & set(rel)
    return len(got) / len(rel)


def ndcg_at_k(ranked, rel, k):
    rel = set(rel)
    dcg = sum(1.0 / math.log2(i + 2) for i, (cid, _) in enumerate(ranked[:k]) if cid in rel)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(rel), k)))
    return dcg / ideal if ideal else 0.0


def reciprocal_rank(ranked, rel):
    rel = set(rel)
    for i, (cid, _) in enumerate(ranked):
        if cid in rel:
            return 1.0 / (i + 1)
    return 0.0


def bootstrap_ci(vals, n_boot=1000, seed=42):
    rng = random.Random(seed)
    n = len(vals)
    means = sorted(sum(rng.choice(vals) for _ in range(n)) / n for _ in range(n_boot))
    return [round(means[int(0.025 * n_boot)], 4), round(means[int(0.975 * n_boot)], 4)]
