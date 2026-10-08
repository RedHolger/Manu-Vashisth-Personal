# EvidenceRAG — tenant-isolated answers with citations

Ask questions over your documents and get answers that cite their sources —
or abstain when nothing supports an answer. Tenants cannot see each other's
content, versions, or caches. Python, FastAPI, PostgreSQL + pgvector.

## How it works

- Versioned ingestion: chunk IDs are content hashes, so edits, deletions and
  revocations invalidate exactly the right candidates and caches.
- Keyword, vector (BAAI/bge-small-en-v1.5) and hybrid retrieval over one
  labeled corpus.
- A model adapter allows one read-only structured tool; every argument is
  validated, every claim must match an authorized citation verbatim, and
  injected instructions in documents are treated as data.

## Run it (needs Docker + Python venv)

```sh
docker compose up -d        # pgvector/pg16
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -p 'test_*.py'
```

Recorded: 124 tests; tenant-isolation probes blocked; held-out evaluation on
a licensed corpus with independent citation review. Human citation sign-off
is still pending — no answer here is human-reviewed.

## Limits

The reference adapter is deterministic and extractive (no real LLM behind
it); quality numbers are fixture-bound. No similarity floor is configured
(`similarity_floor: null`, pinned by a test). One read-only tool only.
