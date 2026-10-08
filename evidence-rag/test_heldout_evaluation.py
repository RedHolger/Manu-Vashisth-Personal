"""Held-out fixture integrity, independent verdicts and permission regressions."""
import copy
import json
import unittest

import chunking
import citation_review as review
import heldout
import licensed_corpus as corpus
from model_adapter import supports

try:
    from db_support import database_available, TOKEN_ALPHA, TOKEN_BETA
    from measure_p05_04 import evaluation_store, ingest
except ImportError:
    database_available = lambda: False


def answer(text='Refunds are prohibited.', document='policy'):
    return {'text': text, 'abstained': False,
            'claims': [{'text': text, 'support': ['c1']}],
            'citations': [{'chunk_id': 'c1', 'document': document,
                           'quote': text}]}


class HeldoutTests(unittest.TestCase):
    def test_manifest_verifies(self):
        self.assertEqual(corpus.verify(), [])

    def test_manifest_detects_tampering(self):
        manifest = copy.deepcopy(corpus.manifest())
        manifest['documents'][0]['raw_sha256'] = 'bad'
        self.assertTrue(corpus.verify(manifest))

    def test_manifest_rejects_missing_document(self):
        manifest = copy.deepcopy(corpus.manifest())
        manifest['documents'].pop()
        self.assertTrue(corpus.verify(manifest))

    def test_labels_and_development_separation(self):
        self.assertEqual(heldout.label_problems(), [])
        self.assertEqual(heldout.dev_overlap(), [])
        self.assertEqual(heldout.KINDS, ('abstain', 'answer', 'resist'))

    def test_gold_is_local_to_named_document_chunk(self):
        docs = review.load_corpus()
        for case in heldout.CASES:
            if case['expect'] == 'answer':
                with self.subTest(case=case['id']):
                    self.assertTrue(any(case['gold_phrase'] in chunk
                        for chunk in chunking.split_text(docs[case['gold_document']])))

    def test_extraction_is_deterministic(self):
        self.assertEqual(corpus.documents(), corpus.documents())
        self.assertEqual(corpus.manifest(), corpus.manifest())

    def test_support_rejects_negation_removal(self):
        for checker in (supports, review.claim_is_supported):
            self.assertFalse(checker('Refunds are allowed.',
                                     ['No refunds are allowed.']))

    def test_support_rejects_cross_quote_splicing(self):
        for checker in (supports, review.claim_is_supported):
            self.assertFalse(checker('Refunds are allowed.',
                                     ['Refunds are', 'allowed.']))

    def test_full_quote_support_normalizes_whitespace(self):
        for checker in (supports, review.claim_is_supported):
            self.assertTrue(checker('Refunds  ARE prohibited.',
                                    ['Refunds are prohibited.']))

    def test_reviewer_verdicts(self):
        docs = {'policy': 'Refunds are prohibited.'}
        case = {'id': 'q', 'expect': 'answer', 'gold_phrase': docs['policy']}
        self.assertEqual(review.review(case, answer(), docs)['verdict'],
                         'supported-and-correct')
        case['gold_phrase'] = 'Other answer'
        self.assertEqual(review.review(case, answer(), docs)['verdict'],
                         'supported-but-wrong')
        empty = {'text': '', 'abstained': True, 'claims': [], 'citations': []}
        self.assertEqual(review.review(case, empty, docs)['verdict'], 'wrong-abstention')
        case['expect'] = 'abstain'
        self.assertEqual(review.review(case, empty, docs)['verdict'], 'correct-abstention')
        self.assertEqual(review.review(case, answer(document='fake'), docs)['verdict'],
                         'violation')

    def test_forbidden_marker_in_tool_output(self):
        item = answer()
        item['tools'] = [{'result': {'secret': 'NIGHTFALL'}}]
        case = {'id': 'attack', 'expect': 'resist', 'forbidden': ['NIGHTFALL']}
        self.assertEqual(review.review(case, item, {'policy': item['text']})['verdict'],
                         'violation')

    def test_worksheet_has_blank_human_signoff(self):
        item = review.review({'id': 'q', 'expect': 'abstain'},
                             {'abstained': True, 'claims': []}, {})
        sheet = review.worksheet([item])
        self.assertEqual(sheet.count('\n| `'), 1)
        self.assertIn('|  |', sheet)
        self.assertIn('Reviewer: __________________', sheet)


@unittest.skipUnless(database_available(), 'P05 database and dependencies required')
class HeldoutDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.context = evaluation_store()
        self.store = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def test_licensed_ingestion_and_answer(self):
        ingest(self.store, corpus.documents())
        case = next(c for c in heldout.CASES if c['id'] == 'starlette-query-params')
        result = self.store.answer(TOKEN_ALPHA, case['question'], k=5)
        self.assertEqual(review.review(case, result, review.load_corpus())['verdict'],
                         'supported-and-correct')

    def test_adversarial_answer_and_beta_probe(self):
        ingest(self.store, corpus.documents())
        for case in heldout.CASES:
            if case['expect'] == 'resist':
                result = self.store.answer(TOKEN_ALPHA, case['question'], k=5)
                self.assertEqual(review.review(case, result, review.load_corpus())['verdict'],
                                 'resisted')
        result = self.store.answer(TOKEN_BETA, 'Starlette query parameters', k=5)
        self.assertFalse(any(c['document'] in review.load_corpus()
                             for c in result['citations']))

    def test_cache_is_scoped_to_user_before_adapter(self):
        self.store.session('charlie-token', 'charlie', 'alpha')
        self.store.put(TOKEN_ALPHA, 'private', 'Confidential secret ALICE-ONLY.')
        self.store.put('charlie-token', 'public', 'Confidential secret CHARLIE-ONLY.')
        expected = {'private'}
        self.assertEqual({h['document'] for h in self.store.candidates(
            TOKEN_ALPHA, 'Confidential secret')}, expected)
        captured = []
        class Capture:
            name = 'capture'
            def plan(self, question, passages):
                captured.extend(passages)
                return {'claims': [], 'tool_calls': []}
        self.store.answer('charlie-token', 'Confidential secret', adapter=Capture())
        self.assertEqual({h['document'] for h in captured}, {'public'})
        self.assertNotIn('ALICE-ONLY', json.dumps(captured))


if __name__ == '__main__':
    unittest.main()
