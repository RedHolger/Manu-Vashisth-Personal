# DiscoveryEval — lexical/dense/hybrid/rerank comparison (role 08)

Frozen synthetic catalog (60 products) + 24 queries with qrels (18 standard,
6 cold-start). No downloads, no services. See LIMITATIONS.md.

## Setup (.venv-builds: numpy)

```
python -m unittest discover -s tests -v
python measure.py   # -> results/measure.json
```

`src/generate.py` built the frozen `datasets/` (seed 11, overlap contracts
asserted); rerun only to verify, not to modify.

## Layout

- `SPEC.md`, `PROVENANCE.md`.
- `src/retrieve.py` (4 methods), `src/metrics.py` (recall/NDCG/MRR/bootstrap).
- `datasets/` (catalog/queries/qrels, frozen), `measure.py`.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
