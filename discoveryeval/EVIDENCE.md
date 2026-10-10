# DiscoveryEval — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 + numpy 2.2.6. Deterministic
except wall-clock latency (excluded from determinism test).

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 7/7 OK (metric hand-checks,
  frozen contracts, determinism, bounds).
- `python measure.py` → `results/measure.json` (metrics bit-identical reruns).

## Measured behavior (24 queries = 18 standard + 6 cold)

| method | recall@5 (CI) | recall@10 | NDCG@10 | MRR | cold r@5 | ms |
|---|---|---|---|---|---|---|
| lexical | 0.667 (0.48–0.83) | 0.813 | 0.587 | 0.534 | 0.0 | 0.24 |
| dense (hashed) | 0.646 (0.46–0.81) | 0.813 | 0.544 | 0.473 | 0.0 | 0.87 |
| hybrid RRF | 0.667 (0.48–0.83) | 0.813 | 0.579 | 0.523 | 0.0 | 1.1 |
| rerank | 0.583 (0.40–0.75) | 0.813 | 0.570 | 0.507 | 0.0 | 1.1 |

CIs overlap: no method significantly best on this set (reported, not hidden).
Cold slice 0.0 everywhere: zero term overlap defeats term methods — the honest
motivation for neural embeddings, not a claim about them.

## Claim basis for CV 08 (role 08 only)

- "Extended catalogue retrieval in an isolated eval: lexical, hashed-dense,
  hybrid and rerank compared on a frozen 24-query set with recall/NDCG/MRR,
  bootstrap uncertainty and a cold-start slice."
- "No engagement gains, no neural-model or big-data claims."
