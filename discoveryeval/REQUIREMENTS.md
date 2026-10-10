# DiscoveryEval — requirements map

| Requirement (BUILD_PROMPTS ranking) | Check | Result |
|---|---|---|
| Isolated Kensaku extension | standalone; no Kensaku code/data reused | done |
| Licensed data + frozen split | synthetic owned corpus; 60 docs, 24 queries committed | done |
| Lexical/dense/hybrid/rerank compare | BM25 / hashed-TF / RRF / title-boost rerank | done |
| recall@k/NDCG/MRR/latency | @5/@10, NDCG@10, MRR, mean ms per method | pass |
| Query counts + seeds | 24 = 18 + 6; seeds 11 (data) / 42 (bootstrap) | pass |
| Uncertainty | bootstrap 95% CI on recall@5 | pass |
| Cold-start slice | recall@5 = 0.0 all methods (reported, motivates neural models) | pass |
| No online/production claims | LIMITATIONS.md | stated |
| Spark preparation (optional) | not installed; single-machine scale | SKIPPED |
