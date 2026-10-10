# GenAI Privacy Evaluation — canary-leakage harness (role 33)

Self-contained baseline-vs-controls test: does authorization stop canary
leakage? sqlite3 + stdlib only. No P05 code copied (see PROVENANCE.md).

## Setup

```
python measure.py                          # frozen eval -> results/measure.json
python -m unittest discover -s tests -v    # 8 tests (runs measure.py once)
```

## Layout

- `SPEC.md` — store, pipeline, datasets, metrics, expected direction.
- `PROVENANCE.md` — P05 alignment without code reuse.
- `src/store.py` — tenants, versions, revocation, synthetic canaries.
- `src/retrieval.py` — minimal BM25. `src/answer.py` — extractive pipeline.
- `datasets/attacks.json` (12) + `datasets/benign.json` (8), frozen.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
