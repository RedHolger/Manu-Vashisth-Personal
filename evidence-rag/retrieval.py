"""Pure ranking functions shared by every retrieval mode.

No database access here: the store filters by tenant and membership first and
then hands the visible chunks to these functions, so an authorization bug can
never be hidden inside a scorer.

* `bm25_rank`   — keyword retrieval (Lucene-flavoured BM25, k1=1.2, b=0.75).
* `rrf_fuse`    — hybrid retrieval by reciprocal rank fusion (k=60), which needs
                  no training labels and therefore cannot overfit the labeled
                  corpus used to evaluate it.
"""
import math

from chunking import question_terms

RRF_K = 60

# Conventional English function words. Both sides of the comparison are filtered
# with the same list, so the benchmark measures ranking rather than whether one
# retriever happens to be carrying a stopword table. Negations are deliberately
# kept: "not covered" must not collapse into "covered".
STOPWORDS = frozenset("""
a an the and or but if then else of to in on at for from by with as into
about over under out up down off than too very can will just do does did
doing is are was were be been being have has had having this that these
those it its i me my we our you your he she they them their us
what which who whom whose when where why how all any both each few more
most other some such only own same so now
don t
""".split())


def bm25(question, chunks, k1=1.2, b=0.75):
    """Score every visible chunk; returns {chunk_id: score} (0.0 for no match).

    Inverse document frequency is computed over the whole visible set handed in —
    the caller passes every chunk the caller may read, not just the matching
    ones, so rare terms inside the tenant's corpus rank higher than terms that
    appear everywhere in it.
    """
    terms = [term for term in question_terms(question)
             if term not in STOPWORDS]
    if not terms:
        return {}
    total = len(chunks)
    if total == 0:
        return {}
    document_terms = [[term for term in chunk['terms']
                       if term not in STOPWORDS] for chunk in chunks]
    average_length = sum(len(terms_for_chunk)
                         for terms_for_chunk in document_terms) / total
    document_frequency = {}
    for terms_for_chunk in document_terms:
        for term in set(terms_for_chunk):
            document_frequency[term] = document_frequency.get(term, 0) + 1
    scores = {}
    for chunk, terms_for_chunk in zip(chunks, document_terms):
        length = len(terms_for_chunk) or 1
        norm = k1 * (1 - b + b * length / average_length)
        score = 0.0
        for term in set(terms):
            if term not in terms_for_chunk:
                continue
            occurrences = terms_for_chunk.count(term)
            # Lucene variant: always positive, so a term present in every chunk
            # can never subtract from a score.
            idf = math.log(1 + (total - document_frequency.get(term, 0) + 0.5)
                           / (document_frequency.get(term, 0) + 0.5))
            score += idf * occurrences * (k1 + 1) / (occurrences + norm)
        if score > 0:
            scores[chunk['chunk_id']] = score
    return scores


def order_by_score(scores, limit=None):
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    return ordered[:limit] if limit else ordered


def rrf_scores(rankings, k=RRF_K):
    """Reciprocal rank fusion: each ranking contributes 1/(k + rank)."""
    scores = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def rrf_fuse(rankings, k=RRF_K, limit=None):
    """The fused order, best first."""
    return order_by_score(rrf_scores(rankings, k), limit)
