# DiscoveryEval — LIMITATIONS

- Synthetic 60-doc catalog; not web scale, not Pinterest data.
- "Dense" is hashed TF-IDF, NOT BGE-M3 or any neural embedding (no download
  attempted); "rerank" is a transparent title-overlap feature, not a
  cross-encoder. Neural-model comparisons are future work, unclaimed.
- Cold-start slice is adversarial by construction (0 term overlap); 0.0 is a
  measurement of term methods' limit, not a model failure.
- Tiny query set (24): CIs wide; no significance claimed between methods.
- No Spark, no Qdrant, no online metrics. Local-machine results only.
- Supports role 08 only as evaluation-methodology work.
