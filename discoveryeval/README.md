# DiscoveryEval

A retrieval experiment on a frozen catalogue of 60 synthetic products and 24 labelled queries. It compares lexical search, hashed-dense search, a hybrid method and reranking using recall, NDCG and MRR.

Six queries form a separate cold-start slice. Keeping that slice visible exposed a weakness that an overall average would hide. Bootstrap intervals show how uncertain the comparisons are on this small dataset.

## Run the comparison

Install NumPy in your Python 3 environment, then run:

```bash
python3 -m unittest discover -s tests -v
python3 measure.py
```

Results go to `results/measure.json`. Retrieval methods live in `src/retrieve.py`; scoring and bootstrap code are in `src/metrics.py`.

The inputs and relevance labels in `datasets/` are frozen. `src/generate.py` recreates them with seed 11, but regeneration is not required to run the evaluation. The dense baseline uses hashing, not a pretrained neural embedding model. See [LIMITATIONS.md](LIMITATIONS.md) before interpreting the scores.
