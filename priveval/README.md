# PrivacyEval

A small retrieval harness for checking whether access controls prevent synthetic secrets from appearing in answers. It runs the same frozen cases against an unprotected baseline and a tenant-scoped, re-authorized path.

The dataset contains 12 attack cases and eight benign queries. Separate checks cover stale caches and revoked access, so a previously valid result cannot silently remain authorized.

## Run the evaluation

Python 3's standard library is sufficient:

```bash
python3 measure.py
python3 -m unittest discover -s tests -v
```

The report is written to `results/measure.json`. `src/store.py` manages tenants, versions and revocation; `src/retrieval.py` implements a small BM25 retriever; `src/answer.py` produces extractive answers.

[SPEC.md](SPEC.md) defines the cases and metrics. [PROVENANCE.md](PROVENANCE.md) records the relationship to the separate EvidenceRAG project. The harness measures authorization behavior on synthetic canaries; it does not test an external LLM or establish a differential-privacy guarantee.
