"""Minimal BM25 scorer (stdlib). Newly written; principle-aligned with P05."""
import math
import re

K1, B = 1.2, 0.75


def toks(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def bm25(query, chunks):
    """chunks: list of dicts with 'id' and 'text'. Returns [(id, score)] desc."""
    q = toks(query)
    docs = [(c["id"], toks(c["text"])) for c in chunks]
    n = len(docs)
    if n == 0 or not q:
        return []
    df = {}
    for _, dt in docs:
        for t in set(dt):
            df[t] = df.get(t, 0) + 1
    avg = sum(len(dt) for _, dt in docs) / n
    out = []
    for cid, dt in docs:
        s = 0.0
        for t in q:
            tf = dt.count(t)
            if not tf:
                continue
            idf = math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(dt) / (avg or 1)))
        out.append((cid, s))
    out.sort(key=lambda p: -p[1])
    return out
