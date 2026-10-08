"""P05-02 versioned ingestion: stable chunk ids and invalidation on every write."""
import unittest

from chunking import make_chunk_id, split_text
from embeddings import embedding_available as _embedder_available
from labeled_corpus import BETA_MARKERS, seed_alpha, seed_beta

try:
    import psycopg

    from db_support import (DOC_ALPHA, TEXT_ALPHA, TOKEN_ALPHA, TOKEN_BETA,
                            database_available, fresh_store)
except Exception as _exc:  # pragma: no cover - exercised only without psycopg
    psycopg = None
    DOC_ALPHA = TOKEN_ALPHA = TOKEN_BETA = str(_exc)
    database_available = fresh_store = None

SKIP = 'psycopg or a reachable P05 database is required'


def _chunk_rows(store, tenant, document_id, version=None):
    sql = ('SELECT version, chunk_index, chunk_id, text FROM chunks '
           'WHERE tenant = %s AND document_id = %s')
    params = [tenant, document_id]
    if version is not None:
        sql += ' AND version = %s'
        params.append(version)
    sql += ' ORDER BY version, chunk_index'
    with store.conn.transaction():
        return store.conn.execute(sql, params).fetchall()


def _cache_rows(store, tenant):
    with store.conn.transaction():
        return store.conn.execute(
            'SELECT question_hash, mode FROM retrieval_cache WHERE tenant = %s',
            (tenant,)).fetchall()


def _generation(store, tenant):
    with store.conn.transaction():
        row = store.conn.execute(
            'SELECT generation FROM tenant_generation WHERE tenant = %s',
            (tenant,)).fetchone()
    return int(row['generation']) if row else 0


@unittest.skipUnless(psycopg is not None and database_available(), SKIP)
class VersionedIngestionTests(unittest.TestCase):
    def setUp(self):
        self.ctx = fresh_store()
        self.store = self.ctx.__enter__()
        seed_alpha(self.store, TOKEN_ALPHA)
        seed_beta(self.store, TOKEN_BETA)

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    # ------------------------------------------------------------ stable ids
    def test_reingesting_identical_text_reproduces_the_same_chunk_ids(self):
        original = TEXT_ALPHA
        before = [(row['chunk_index'], row['chunk_id'], row['text'])
                  for row in _chunk_rows(self.store, 'alpha', DOC_ALPHA, 1)]
        self.assertTrue(before)
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, original)   # forces version 2
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, original)   # forces version 3
        after = [(row['chunk_index'], row['chunk_id'], row['text'])
                 for row in _chunk_rows(self.store, 'alpha', DOC_ALPHA, 3)]
        self.assertEqual([index for index, _, _ in after],
                         [index for index, _, _ in before])
        self.assertEqual([chunk_id for _, chunk_id, _ in after],
                         [chunk_id for _, chunk_id, _ in before])
        self.assertEqual([text for _, _, text in after],
                         [text for _, _, text in before])

    def test_id_matches_the_documented_derivation(self):
        rows = _chunk_rows(self.store, 'alpha', DOC_ALPHA, 1)
        for row in rows:
            self.assertEqual(
                row['chunk_id'],
                make_chunk_id('alpha', DOC_ALPHA, row['chunk_index'],
                              row['text']))

    def test_editing_one_sentence_changes_only_that_chunk_id(self):
        original = {row['chunk_index']: row
                    for row in _chunk_rows(self.store, 'alpha', DOC_ALPHA, 1)}
        edited = 'Refunds take five working days. Support is open on Tuesdays.'
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, edited)
        current = {row['chunk_index']: row
                   for row in _chunk_rows(self.store, 'alpha', DOC_ALPHA, 2)}
        self.assertEqual(original[0]['chunk_id'], current[0]['chunk_id'])
        self.assertNotEqual(original[1]['chunk_id'], current[1]['chunk_id'])
        self.assertEqual(current[1]['text'], 'Support is open on Tuesdays.')
        # Two chunks in the fixture, so splitting is doing what the corpus says.
        self.assertEqual(len(current), 2)

    def test_chunk_id_always_resolves_to_the_same_text(self):
        # An id may recur across versions when the chunk text is unchanged; what
        # must never happen is one id meaning two different texts.
        with self.store.conn.transaction():
            rows = self.store.conn.execute(
                'SELECT chunk_id, count(DISTINCT text) AS variants '
                'FROM chunks WHERE tenant = %s '
                'GROUP BY chunk_id HAVING count(DISTINCT text) > 1',
                ('alpha',)).fetchall()
        self.assertEqual(rows, [])

    # ------------------------------------------------------------- versions
    def test_every_version_is_recorded_with_its_checksum_and_chunk_count(self):
        self.store.put(TOKEN_ALPHA, DOC_ALPHA,
                       'Refunds take ten days. Support is open on Tuesdays.')
        with self.store.conn.transaction():
            rows = self.store.conn.execute(
                'SELECT version, checksum, chunk_count FROM document_versions '
                'WHERE tenant = %s AND document_id = %s ORDER BY version',
                ('alpha', DOC_ALPHA)).fetchall()
        self.assertEqual([row['version'] for row in rows], [1, 2])
        for row in rows:
            self.assertEqual(len(row['checksum']), 64)
        self.assertEqual(rows[0]['chunk_count'], 2)
        self.assertEqual(rows[1]['chunk_count'], 2)

    def test_old_version_chunks_are_retained_but_never_returned(self):
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, 'Retired sentence about refunds.')
        # The phrase only exists in version 1, which is retained but not ranked.
        hits = self.store.candidates(TOKEN_ALPHA, 'working days')
        # The corpus documents still match; the superseded version must not.
        self.assertNotIn(DOC_ALPHA, [hit['document'] for hit in hits])
        rows = _chunk_rows(self.store, 'alpha', DOC_ALPHA, 1)
        self.assertTrue(any('five working days' in row['text'] for row in rows))
        with self.store.conn.transaction():
            current = self.store.conn.execute(
                'SELECT count(*) AS n FROM chunks WHERE tenant = %s '
                'AND document_id = %s AND version = 2', ('alpha', DOC_ALPHA)
            ).fetchone()
        self.assertEqual(current['n'], 1)

    # ------------------------------------------------------- invalidation
    def test_put_delete_and_revoke_each_bump_the_generation(self):
        start = _generation(self.store, 'alpha')
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, 'Refunds take five working days.')
        after_put = _generation(self.store, 'alpha')
        self.assertGreater(after_put, start)
        self.store.delete(TOKEN_ALPHA, DOC_ALPHA)
        after_delete = _generation(self.store, 'alpha')
        self.assertGreater(after_delete, after_put)

        self.store.put(TOKEN_ALPHA, 'fresh', 'Fresh document about refunds.')
        self.store.candidates(TOKEN_ALPHA, 'refunds')
        self.assertTrue(_cache_rows(self.store, 'alpha'))
        self.store.revoke(TOKEN_ALPHA, 'fresh')
        self.assertEqual(_generation(self.store, 'alpha'), after_delete + 2)
        self.assertEqual(_cache_rows(self.store, 'alpha'), [])

    def test_cached_ranking_is_dropped_when_a_document_is_deleted(self):
        first = self.store.candidates(TOKEN_ALPHA, 'refunds')
        self.assertTrue(first)
        self.assertTrue(_cache_rows(self.store, 'alpha'))
        self.store.delete(TOKEN_ALPHA, DOC_ALPHA)
        self.assertEqual(_cache_rows(self.store, 'alpha'), [])
        self.assertEqual(self.store.candidates(TOKEN_ALPHA, 'refunds'), [])

    def test_revocation_removes_the_document_from_a_cached_ranking(self):
        self.assertTrue(self.store.candidates(TOKEN_ALPHA, 'refunds'))
        self.store.revoke(TOKEN_ALPHA, DOC_ALPHA)
        self.assertEqual(_cache_rows(self.store, 'alpha'), [])
        self.assertEqual(self.store.candidates(TOKEN_ALPHA, 'refunds'), [])

    # ------------------------------------------------- stale content leaks
    def test_version_change_rejects_a_carried_over_citation(self):
        stale = self.store.candidates(TOKEN_ALPHA, 'refunds')
        self.assertTrue(stale)
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, 'Refunds take ten days.')
        self.assertTrue(self.store.finalize(TOKEN_ALPHA, 'refunds',
                                            stale)['abstained'])

    def test_old_text_never_appears_in_a_new_ranking_or_answer(self):
        old_quote = 'Zzyzx refund window is seven days.'
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, old_quote)
        self.assertIn(old_quote,
                      [hit['quote'] for hit in
                       self.store.candidates(TOKEN_ALPHA, 'Zzyzx')])
        self.store.put(TOKEN_ALPHA, DOC_ALPHA, 'Zzyzx refund window is three days.')
        hits = self.store.candidates(TOKEN_ALPHA, 'Zzyzx')
        self.assertNotIn(old_quote, [hit['quote'] for hit in hits])
        answer = self.store.query(TOKEN_ALPHA, 'Zzyzx')
        self.assertNotIn(old_quote, answer['text'])

    def test_history_revalidates_the_chunk_id_not_just_the_version(self):
        self.store.query(TOKEN_ALPHA, 'refunds')
        stored = self.store.history(TOKEN_ALPHA)[0]['citations']
        self.assertTrue(stored)
        with self.store.conn.transaction():
            self.store.conn.execute(
                'UPDATE chunks SET text = %s '
                'WHERE tenant = %s AND document_id = %s AND version = 1',
                ('rewritten text', 'alpha', DOC_ALPHA))
        after = self.store.history(TOKEN_ALPHA)[0]['citations']
        self.assertEqual(after, [])

    # ------------------------------------------------------ cross tenant
    def test_no_alpha_result_contains_a_beta_marker_in_any_mode(self):
        for mode in ('keyword', 'vector', 'hybrid'):
            if mode != 'keyword' and not _embedder_available():
                continue
            hits = self.store.candidates(TOKEN_ALPHA, 'rotate the key',
                                         mode=mode)
            body = ' '.join(hit['quote'] for hit in hits)
            for marker in BETA_MARKERS:
                self.assertNotIn(marker, body, mode)


if __name__ == '__main__':
    unittest.main()
