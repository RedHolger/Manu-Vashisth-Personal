"""P05-02 retrieval: BM25, vector, hybrid — and what each one may never return."""
import json
import unittest

from chunking import MAX_CHARS, split_text
from embeddings import embedding_available
from labeled_corpus import (BETA_MARKERS, DOCUMENTS, QUESTIONS, seed_alpha,
                            seed_beta)
from retrieval import bm25, order_by_score, rrf_fuse, rrf_scores

try:
    import psycopg

    from db_support import TOKEN_ALPHA, TOKEN_BETA, database_available, fresh_store
    from pg_store import MODES, ModeUnavailable
except Exception:  # pragma: no cover - no driver on system python
    psycopg = None
    TOKEN_ALPHA = TOKEN_BETA = None
    database_available = fresh_store = None
    MODES = ()
    ModeUnavailable = RuntimeError

SKIP = 'psycopg or a reachable P05 database is required'


def _chunks_from_corpus():
    rows = []
    for document in DOCUMENTS:
        for index, text in enumerate(split_text(document['text'])):
            rows.append({'chunk_id': '%s:%d' % (document['id'], index),
                         'text': text,
                         'terms': text.lower().split()})
    return rows


class ChunkingTests(unittest.TestCase):
    def test_two_sentences_become_two_chunks(self):
        self.assertEqual(split_text('One here. Two here.'), ['One here.',
                                                            'Two here.'])

    def test_blank_input_produces_no_chunks(self):
        self.assertEqual(split_text('   \n  '), [])

    def test_oversized_sentence_is_wrapped(self):
        long_text = ' '.join(['word'] * 400)
        chunks = split_text(long_text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= MAX_CHARS for chunk in chunks))
        self.assertEqual(' '.join(chunks), long_text)


class LabeledCorpusTests(unittest.TestCase):
    def test_every_gold_label_points_at_a_real_chunk(self):
        for question in QUESTIONS:
            for document_id, chunk_index in question['gold']:
                document = next(d for d in DOCUMENTS if d['id'] == document_id)
                pieces = split_text(document['text'])
                self.assertLess(chunk_index, len(pieces),
                                question['id'])
                self.assertTrue(pieces[chunk_index].strip(), question['id'])

    def test_corpus_shape_is_what_the_evidence_claims(self):
        self.assertEqual(len(DOCUMENTS), 9)
        self.assertEqual(sum(len(split_text(d['text'])) for d in DOCUMENTS), 18)
        self.assertEqual(len(QUESTIONS), 14)
        self.assertEqual(sum(1 for q in QUESTIONS if q['gold']), 13)


class RankingTests(unittest.TestCase):
    def test_bm25_only_scores_chunks_that_contain_a_query_term(self):
        chunks = _chunks_from_corpus()
        scores = bm25('refund working days', chunks)
        self.assertTrue(scores)
        self.assertIn('refunds:0', scores)
        self.assertNotIn('invoices:0', scores)

    def test_bm25_ranks_a_rarer_term_above_a_common_one(self):
        chunks = [{'chunk_id': 'a', 'terms': 'rare term here'.split()},
                  {'chunk_id': 'b', 'terms': 'common term here'.split()},
                  {'chunk_id': 'c', 'terms': 'common other here'.split()}]
        scores = bm25('common term', chunks)
        order = order_by_score(scores)
        self.assertEqual(order[0], 'b')
        self.assertGreater(scores['b'], scores['a'])

    def test_bm25_returns_nothing_for_an_empty_question(self):
        self.assertEqual(bm25('   ', _chunks_from_corpus()), {})

    def test_rrf_puts_an_id_ranked_first_by_both_lists_first(self):
        fused = rrf_fuse([['x', 'y', 'z'], ['x', 'a', 'b']])
        self.assertEqual(fused[0], 'x')

    def test_rrf_keeps_an_id_that_only_one_list_found(self):
        fused = rrf_fuse([['x', 'y'], ['y', 'a']])
        self.assertEqual(fused[0], 'y')          # found by both lists
        self.assertIn('x', fused)                # only the first list
        self.assertIn('a', fused)                # only the second list

    def test_rrf_ties_break_deterministically_on_chunk_id(self):
        first = rrf_fuse([['x'], ['a']])
        second = rrf_fuse([['x'], ['a']])
        self.assertEqual(first, second)
        self.assertEqual(first[0], 'a')          # equal scores, lower id first
        self.assertEqual(rrf_fuse([['x'], ['a']]), first)

    def test_rrf_is_deterministic_for_ties(self):
        first = rrf_fuse([['b', 'a'], ['a', 'b']])
        second = rrf_fuse([['b', 'a'], ['a', 'b']])
        self.assertEqual(first, second)
        scores = rrf_scores([['b', 'a'], ['a', 'b']])
        self.assertAlmostEqual(scores['a'], scores['b'])


@unittest.skipUnless(psycopg is not None and database_available(), SKIP)
class RetrievalModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not psycopg or not database_available():
            return
        cls.ctx = fresh_store(seed=False)
        cls.store = cls.ctx.__enter__()
        seed_alpha(cls.store, TOKEN_ALPHA)
        seed_beta(cls.store, TOKEN_BETA)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'ctx', None) is not None:
            cls.ctx.__exit__(None, None, None)

    @staticmethod
    def _cache_rows(store, tenant):
        with store.conn.transaction():
            return store.conn.execute(
                'SELECT question_hash, mode FROM retrieval_cache '
                'WHERE tenant = %s', (tenant,)).fetchall()

    def _modes(self):
        return MODES if embedding_available() else ('keyword',)

    def test_default_mode_matches_the_keyword_mode(self):
        default = self.store.candidates(TOKEN_ALPHA, 'refund working days')
        keyword = self.store.candidates(TOKEN_ALPHA, 'refund working days',
                                        mode='keyword')
        self.assertEqual(default, keyword)
        self.assertTrue(keyword)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.candidates(TOKEN_ALPHA, 'refund', mode='fuzzy')

    def test_every_mode_returns_only_this_tenant_s_documents(self):
        for mode in self._modes():
            hits = self.store.candidates(TOKEN_ALPHA, 'rotate NIGHTFALL key',
                                         mode=mode)
            body = json.dumps(hits)
            for marker in BETA_MARKERS:
                self.assertNotIn(marker, body, mode)
            allowed = {document['id'] for document in DOCUMENTS}
            self.assertEqual({hit['document'] for hit in hits} - allowed,
                             set(), mode)
            if mode == 'keyword':
                # Nothing in the alpha corpus matches these terms.
                self.assertEqual(hits, [], mode)

    def test_unanswerable_question_makes_keyword_abstain(self):
        answer = self.store.query(
            TOKEN_ALPHA, 'airspeed velocity of an unladen swallow',
            mode='keyword')
        self.assertTrue(answer['abstained'])
        self.assertEqual(answer['citations'], [])
        self.assertEqual(answer['text'],
                         'No authorized supporting passage found.')
        self.assertEqual(answer['mode'], 'keyword')

    def test_vector_and_hybrid_have_no_similarity_floor_in_this_card(self):
        # P05-02 ships no cosine threshold, so a semantic ranking always fills
        # every slot and cannot abstain. Abstention for those modes belongs to
        # P05-03 and is recorded in LIMITATIONS; pinning it here means adding a
        # floor later is a deliberate, visible change.
        if not embedding_available():
            self.skipTest('embedding adapter not installed')
        for mode in ('vector', 'hybrid'):
            hits = self.store.candidates(
                TOKEN_ALPHA, 'airspeed velocity of an unladen swallow',
                mode=mode)
            self.assertEqual(len(hits), 3, mode)
            answer = self.store.query(
                TOKEN_ALPHA, 'airspeed velocity of an unladen swallow',
                mode=mode)
            self.assertFalse(answer['abstained'], mode)
            self.assertEqual(answer['mode'], mode)

    def test_hybrid_contains_ids_found_by_either_single_ranking(self):
        if not embedding_available():
            self.skipTest('embedding adapter not installed')
        keyword = {hit['chunk_id'] for hit in self.store.candidates(
            TOKEN_ALPHA, 'refund working days', mode='keyword')}
        vector = {hit['chunk_id'] for hit in self.store.candidates(
            TOKEN_ALPHA, 'refund working days', mode='vector')}
        hybrid = {hit['chunk_id'] for hit in self.store.candidates(
            TOKEN_ALPHA, 'refund working days', mode='hybrid')}
        self.assertTrue(keyword and vector)
        self.assertTrue(hybrid <= (keyword | vector))
        self.assertTrue(hybrid & keyword)
        self.assertTrue(hybrid & vector)

    def test_vector_scores_are_cosine_similarities(self):
        if not embedding_available():
            self.skipTest('embedding adapter not installed')
        hits = self.store.candidates(TOKEN_ALPHA, 'refund working days',
                                     mode='vector')
        self.assertTrue(hits)
        for hit in hits:
            self.assertGreaterEqual(hit['score'], -1.0)
            self.assertLessEqual(hit['score'], 1.0)

    def test_vector_mode_reports_a_missing_adapter_instead_of_degrading(self):
        if embedding_available():
            self.skipTest('adapter present; the failure path needs it absent')
        with self.assertRaises(ModeUnavailable):
            self.store.candidates(TOKEN_ALPHA, 'refund', mode='vector')

    def test_cache_serves_the_ranking_until_the_generation_moves(self):
        first = self.store.candidates(TOKEN_ALPHA, 'working days')
        self.assertTrue(first)
        self.assertTrue(self._cache_rows(self.store, 'alpha'))
        with self.store.conn.transaction():
            self.store.conn.execute(
                'UPDATE retrieval_cache SET hits = %s WHERE tenant = %s',
                ('[]', 'alpha'))
        self.assertEqual(
            self.store.candidates(TOKEN_ALPHA, 'working days'), [])
        # Any write moves the generation, which makes the cached row unusable.
        self.store.put(TOKEN_ALPHA, 'refunds',
                       'Refunds take five working days. Nothing else here.')
        self.assertEqual(self._cache_rows(self.store, 'alpha'), [])
        self.assertTrue(
            self.store.candidates(TOKEN_ALPHA, 'working days'))

    def test_hits_carry_a_chunk_id_for_every_mode(self):
        for mode in self._modes():
            hits = self.store.candidates(TOKEN_ALPHA, 'warranty',
                                         mode=mode)
            for hit in hits:
                self.assertEqual(len(hit['chunk_id']), 64, mode)
                self.assertIn('chunk', hit)
                self.assertIn('quote', hit)


if __name__ == '__main__':
    unittest.main()
