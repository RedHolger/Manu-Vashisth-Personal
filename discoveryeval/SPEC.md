# DiscoveryEval — SPEC (Milestone 1)

Scope: lexical/dense/hybrid/rerank comparison on a frozen synthetic catalog,
for role 08 (Pinterest ML). No model downloads, no Qdrant/Docker, no Spark.

## Corpus (synthetic, generated once by `src/generate.py`, seed 11, committed)

- 60 industrial products: 6 categories × 10 (gate valves, centrifugal pumps,
  proximity sensors, ball bearings, control cables, hydraulic filters).
- Each: id, title, description, category. Titles use category terms;
  descriptions mix shared + distinctive terms.
- 24 frozen queries with qrels (1–2 relevant each):
  - 18 standard: share ≥2 content terms with ≥1 relevant doc (asserted).
  - 6 cold-start: share 0 content terms with their relevant docs, using only
    synonym-pool words (asserted); e.g. "fluid mover" → centrifugal pump docs.

## Methods (all local; numpy + stdlib)

- lexical: BM25 (k1=1.2, b=0.75) over title+description.
- dense: hashed TF vectors (dim 512, sha256-stable buckets), L2 cosine.
  Labeled a BASELINE, not BGE-M3 (no download attempted).
- hybrid: RRF k=60 over lexical + dense ranks.
- rerank: hybrid top-10 rescored by RRF score + title-term-overlap fraction.
  Transparent feature rerank, not a cross-encoder (stated).

## Metrics (measure.py → results/measure.json)

recall@5, recall@10, NDCG@10, MRR per method; mean latency per method;
cold-start slice recall@5; bootstrap 95% CI (1000 resamples, seed 42) for
recall@5; query counts (24 = 18 + 6), seeds recorded.

## Out of scope (SKIPPED, not successful)

- BGE-M3/ColBERT neural models (multi-GB downloads not attempted).
- Spark preparation (single-machine scale; PySpark not installed).
- Any online-engagement or production big-data claim.
