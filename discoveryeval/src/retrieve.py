"""Retrievers: BM25, hashed-dense cosine, RRF hybrid, title-boost rerank."""
import hashlib
import math
import re

import numpy as np

STOP = {"and", "with", "for", "the", "a", "of", "in", "to", "per"}


def toks(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def doc_text(d):
    return d["title"] + " " + d["description"]


def bm25(query, docs, k1=1.2, b=0.75):
    q = toks(query)
    dd = [(d["id"], toks(doc_text(d))) for d in docs]
    n = len(dd)
    df = {}
    for _, dt in dd:
        for t in set(dt):
            df[t] = df.get(t, 0) + 1
    avg = sum(len(dt) for _, dt in dd) / n
    out = []
    for cid, dt in dd:
        s = 0.0
        for t in q:
            tf = dt.count(t)
            if tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(dt) / avg))
        out.append((cid, s))
    out.sort(key=lambda p: -p[1])
    return out


def hashed_vec(terms, dim=512):
    v = np.zeros(dim)
    for t in terms:
        v[int(hashlib.sha256(t.encode()).hexdigest(), 16) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def dense(query, docs, dim=512):
    qv = hashed_vec(toks(query), dim)
    out = []
    for d in docs:
        dv = hashed_vec(toks(doc_text(d)), dim)
        out.append((d["id"], float(qv @ dv)))
    out.sort(key=lambda p: -p[1])
    return out


def rrf(rankings, k=60):
    fused = {}
    for r in rankings:
        for rank, (cid, _) in enumerate(r):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda p: -p[1])


def hybrid(query, docs):
    return rrf([bm25(query, docs), dense(query, docs)])


def rerank(query, docs, topn=10):
    """Transparent feature rerank of hybrid top-10: RRF score + title overlap."""
    hyb = dict(hybrid(query, docs))
    top = sorted(hyb.items(), key=lambda p: -p[1])[:topn]
    by_id = {d["id"]: d for d in docs}
    qt = set(toks(query))
    out = []
    for cid, s in top:
        tt = set(toks(by_id[cid]["title"]))
        boost = len(qt & tt) / max(1, len(qt))
        out.append((cid, s + boost))
    out.sort(key=lambda p: -p[1])
    return out


METHODS = {"lexical": bm25, "dense": dense, "hybrid": hybrid, "rerank": rerank}
