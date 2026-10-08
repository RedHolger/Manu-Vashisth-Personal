"""Local embedding adapter.

One model, `BAAI/bge-small-en-v1.5`, whose output dimension (384) is exactly the
dimension declared by migration 0001/0002. The model runs on ONNX Runtime through
`fastembed`, so it is a local, offline-capable adapter once the weights are
cached; no paid API and no outbound call is made at query time.

The dependency is optional on purpose: `embedding_available()` lets the keyword
path, the versioning path and every invalidation test run on a plain system
Python, while vector and hybrid retrieval report a clear error instead of
silently degrading to keyword results.
"""
import hashlib

MODEL_NAME = 'BAAI/bge-small-en-v1.5'
DIMENSION = 384

_model = None
_load_failed = False


def embedding_available():
    try:
        import fastembed  # noqa: F401
    except Exception:
        return False
    return True


def _load():
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        raise RuntimeError('embedding model failed to load previously')
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL_NAME)
    except Exception:
        _load_failed = True
        raise
    return _model


def embed(texts):
    """Embed a list of strings; returns a list of 384-float vectors."""
    if not texts:
        return []
    model = _load()
    return [list(map(float, vector)) for vector in model.embed(texts)]


def embed_one(text):
    return embed([text])[0]


def vector_literal(vector):
    """Format a vector for `%s::vector` — pgvector accepts the JSON array form."""
    return '[' + ','.join('%.6f' % value for value in vector) + ']'


def question_fingerprint(question):
    return hashlib.sha256(question.encode('utf-8')).hexdigest()
