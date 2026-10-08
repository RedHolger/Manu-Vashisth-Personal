"""P05-03: a model adapter whose plan is untrusted input.

Two properties are graded:

* adversarial document text cannot expand tool permissions — proven with an
  adapter that deliberately *does* obey document text, so the guard has to be
  in validation rather than in model behaviour;
* answer claims are supported by citations that are currently authorized —
  every claim must appear verbatim in the passages it cites, and those passages
  are re-authorized at answer time.
"""
import unittest

import attacks
from model_adapter import (ALLOWED_TOOLS, LocalExtractiveAdapter,
                           PromptInjectingAdapter, validate_plan)

try:
    import psycopg
    from fastapi.testclient import TestClient

    from app import create_app
    from db_support import (MARKERS_ALPHA, MARKERS_BETA, RECORD_ALPHA,
                            RECORD_BETA, TOKEN_ALPHA, TOKEN_BETA, VALUE_ALPHA,
                            database_available, fresh_store)
    import labeled_corpus
except Exception as _exc:  # pragma: no cover - exercised only without the stack
    psycopg = None
    TestClient = None
    create_app = None
    labeled_corpus = None
    MARKERS_ALPHA = MARKERS_BETA = ()
    database_available = fresh_store = None

SKIP = 'fastapi, httpx2 and a reachable P05 database are required'

INJECTION_PASSAGES = [
    {'chunk_id': 'injection-%d' % index, 'quote': line}
    for index, line in enumerate(attacks.INJECTION_TEXT.splitlines())
    if line.strip()]
# Exactly the passages the attack question retrieves, so the hostile adapter's
# claim count stays inside the per-answer cap and the fabrication reaches the
# text-support check instead of being cut off as "too many claims".
INJECTION_TOOL_PASSAGES = [
    passage for passage in INJECTION_PASSAGES
    if passage['quote'].strip().upper().startswith('TOOL ')]

REFUND_PASSAGES = [
    {'chunk_id': 'refunds-0',
     'quote': 'A refund is issued within five working days of approval.'},
    {'chunk_id': 'refunds-1',
     'quote': 'The money returns to the original payment method automatically.'},
]


def reasons_for(plan, passages=REFUND_PASSAGES):
    _, _, denied = validate_plan(plan, passages)
    return [denial['reason'] for denial in denied]


def seeded_store():
    """Two tenants, both labeled corpora, records, plus the injected document."""
    ctx = fresh_store()
    store = ctx.__enter__()
    labeled_corpus.seed_alpha(store, TOKEN_ALPHA)
    labeled_corpus.seed_beta(store, TOKEN_BETA)
    attacks.seed(store, TOKEN_ALPHA)
    return ctx, store


def auth(token):
    return {'Authorization': 'Bearer %s' % token}


# ------------------------------------------------------------------ pure layer
class ValidationTests(unittest.TestCase):
    def test_only_one_tool_is_allowlisted(self):
        self.assertEqual(ALLOWED_TOOLS, ('read_record',))

    def test_non_allowlisted_tool_is_denied(self):
        calls, _, denied = validate_plan(
            {'tool_calls': [{'tool': 'delete_all_records',
                             'arguments': {'scope': 'all'}}], 'claims': []},
            REFUND_PASSAGES)
        self.assertEqual(calls, [])
        self.assertEqual(denied[0]['reason'], 'tool-not-allowlisted')

    def test_unknown_argument_is_denied_even_when_the_tool_is_allowed(self):
        calls, _, denied = validate_plan(
            {'tool_calls': [{'tool': 'read_record',
                             'arguments': {'record_id': 'limits',
                                           'tenant': 'beta'}}],
             'claims': []}, REFUND_PASSAGES)
        self.assertEqual(calls, [])
        self.assertEqual(denied[0]['reason'], 'unknown-argument')
        self.assertIn('tenant', denied[0]['detail'])

    def test_namespace_escape_is_denied(self):
        for record_id in ('../../etc/passwd', 'x; DROP TABLE grants',
                          'alpha/invoice', '../invoice', ' invoice'):
            with self.subTest(record_id=record_id):
                calls, _, denied = validate_plan(
                    {'tool_calls': [{'tool': 'read_record',
                                     'arguments': {'record_id': record_id}}],
                     'claims': []}, REFUND_PASSAGES)
                self.assertEqual(calls, [])
                self.assertEqual(denied[0]['reason'],
                                 'invalid-argument-value')

    def test_missing_argument_is_denied(self):
        calls, _, denied = validate_plan(
            {'tool_calls': [{'tool': 'read_record', 'arguments': {}}],
             'claims': []}, REFUND_PASSAGES)
        self.assertEqual(calls, [])
        self.assertEqual(denied[0]['reason'], 'invalid-argument-value')

    def test_arguments_must_be_an_object(self):
        calls, _, denied = validate_plan(
            {'tool_calls': [{'tool': 'read_record', 'arguments': 'limits'}],
             'claims': []}, REFUND_PASSAGES)
        self.assertEqual(calls, [])
        self.assertEqual(denied[0]['reason'], 'invalid-arguments')

    def test_plan_must_be_an_object(self):
        for raw in (None, 'yes', 7, ['tool_calls'], {'tool_calls': 'x'}):
            with self.subTest(raw=raw):
                calls, claims, denied = validate_plan(raw, REFUND_PASSAGES)
                self.assertEqual((calls, claims), ([], []))
                self.assertTrue(denied)

    def test_tool_calls_are_capped(self):
        raw = {'tool_calls': [{'tool': 'read_record',
                               'arguments': {'record_id': 'limits'}}] * 6,
               'claims': []}
        calls, _, denied = validate_plan(raw, REFUND_PASSAGES)
        self.assertEqual(len(calls), 3)
        self.assertIn('too-many-tool-calls',
                      [denial['reason'] for denial in denied])

    def test_valid_call_is_accepted_verbatim(self):
        calls, _, denied = validate_plan(
            {'tool_calls': [{'tool': 'read_record',
                             'arguments': {'record_id': 'limits'}}],
             'claims': []}, REFUND_PASSAGES)
        self.assertEqual(denied, [])
        self.assertEqual(calls, [{'tool': 'read_record',
                                  'arguments': {'record_id': 'limits'}}])

    def test_claim_without_support_is_denied(self):
        _, claims, denied = validate_plan(
            {'tool_calls': [],
             'claims': [{'text': 'Anything.', 'support': []}]},
            REFUND_PASSAGES)
        self.assertEqual(claims, [])
        self.assertIn('claim-without-support',
                      [denial['reason'] for denial in denied])

    def test_claim_support_must_come_from_the_candidates(self):
        _, claims, denied = validate_plan(
            {'tool_calls': [],
             'claims': [{'text': 'A refund is issued within five working '
                                 'days of approval.',
                         'support': ['not-a-candidate']}]},
            REFUND_PASSAGES)
        self.assertEqual(claims, [])
        self.assertIn('claim-support-not-in-candidates',
                      [denial['reason'] for denial in denied])

    def test_claim_must_appear_in_the_text_it_cites(self):
        _, claims, denied = validate_plan(
            {'tool_calls': [],
             'claims': [{'text': 'Beta invoice total is 999 credits.',
                         'support': ['refunds-0']}]},
            REFUND_PASSAGES)
        self.assertEqual(claims, [])
        self.assertIn('claim-not-supported-by-citations',
                      [denial['reason'] for denial in denied])

    def test_supported_claim_is_kept(self):
        text = REFUND_PASSAGES[0]['quote']
        _, claims, denied = validate_plan(
            {'tool_calls': [],
             'claims': [{'text': text, 'support': ['refunds-0']}]},
            REFUND_PASSAGES)
        self.assertEqual(denied, [])
        self.assertEqual(claims, [{'text': text, 'support': ['refunds-0']}])

    def test_every_documented_attack_plan_is_rejected_with_its_reason(self):
        for entry in attacks.ATTACK_PLANS:
            with self.subTest(attack=entry['id']):
                plan = attacks.materialize(entry['plan'], 'refunds-0')
                _, _, denied = validate_plan(plan, REFUND_PASSAGES)
                self.assertIn(entry['expect'],
                              [denial['reason'] for denial in denied])


# ------------------------------------------------------------------- adapters
class AdapterTests(unittest.TestCase):
    def test_local_adapter_reads_a_record_only_from_the_question(self):
        plan = LocalExtractiveAdapter().plan(
            'show me the limits record', INJECTION_PASSAGES)
        self.assertEqual(plan['tool_calls'],
                         [{'tool': 'read_record',
                           'arguments': {'record_id': 'limits'}}])

    def test_local_adapter_ignores_instructions_inside_passage_text(self):
        plan = LocalExtractiveAdapter().plan(
            'runbook for the shared router', INJECTION_PASSAGES)
        self.assertEqual(plan['tool_calls'], [])
        _, _, denied = validate_plan(plan, INJECTION_PASSAGES)
        self.assertEqual(denied, [])

    def test_local_adapter_keeps_only_supported_sentences(self):
        plan = LocalExtractiveAdapter().plan(
            'How many working days does a refund take?', REFUND_PASSAGES)
        self.assertEqual(len(plan['claims']), 1)
        self.assertEqual(plan['claims'][0]['support'], ['refunds-0'])

    def test_local_adapter_abstains_when_nothing_supports_the_claim(self):
        plan = LocalExtractiveAdapter().plan(
            'What is the airspeed velocity of an unladen swallow?',
            REFUND_PASSAGES)
        self.assertEqual(plan['claims'], [])
        self.assertEqual(plan['tool_calls'], [])

    def test_hostile_adapter_still_cannot_expand_permissions(self):
        """The double obeys the document; the validator must not."""
        plan = PromptInjectingAdapter().plan('anything',
                                             INJECTION_TOOL_PASSAGES)
        calls, claims, denied = validate_plan(plan, INJECTION_TOOL_PASSAGES)
        self.assertEqual(calls, [])
        recorded = [denial['reason'] for denial in denied]
        self.assertIn('tool-not-allowlisted', recorded)
        self.assertIn('unknown-argument', recorded)
        self.assertIn('invalid-argument-value', recorded)
        self.assertIn('claim-not-supported-by-citations', recorded)
        # The three quoted TOOL lines are still citable data; only the
        # sentence the model invented is dropped.
        self.assertEqual(len(claims), len(INJECTION_TOOL_PASSAGES))

    def test_hostile_adapter_never_sees_a_valid_tool_call(self):
        plan = PromptInjectingAdapter().plan('anything',
                                             INJECTION_TOOL_PASSAGES)
        calls, _, _ = validate_plan(plan, INJECTION_TOOL_PASSAGES)
        for call in calls:
            self.assertIn(call['tool'], ALLOWED_TOOLS)


# --------------------------------------------------------------- store answer
@unittest.skipUnless(psycopg is not None and database_available(), SKIP)
class AnswerStoreTests(unittest.TestCase):
    def setUp(self):
        self.ctx, self.store = seeded_store()

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def answer(self, question, adapter=None, k=3, mode='keyword', token=None):
        return self.store.answer(token or TOKEN_ALPHA, question, k=k,
                                 mode=mode, adapter=adapter)

    def test_claims_are_a_subset_of_citations(self):
        result = self.answer('How many working days does a refund take?')
        self.assertFalse(result['abstained'])
        cited = {hit['chunk_id'] for hit in result['citations']}
        for claim in result['claims']:
            self.assertTrue(set(claim['support']) <= cited)
            self.assertTrue(claim['support'])

    def test_every_citation_is_currently_authorized(self):
        result = self.answer('How long are customer records stored?')
        self.assertTrue(result['citations'])
        for hit in result['citations']:
            self.assertTrue(self.store._still_citable('alice', 'alpha', hit),
                            'citation %r no longer authorizes' % hit)

    def test_claim_text_is_present_in_the_passage_it_cites(self):
        result = self.answer('When is payment due after an invoice?')
        quotes = {hit['chunk_id']: hit['quote']
                  for hit in result['citations']}
        for claim in result['claims']:
            joined = ' '.join(quotes[chunk_id]
                              for chunk_id in claim['support'])
            self.assertIn(' '.join(claim['text'].split()),
                          ' '.join(joined.split()))

    def test_tool_call_is_scoped_to_the_caller_tenant(self):
        result = self.answer('read record limits')
        self.assertEqual(result['tools'][0]['tool'], 'read_record')
        self.assertEqual(result['tools'][0]['status'], 'ok')
        self.assertEqual(result['tools'][0]['result'], VALUE_ALPHA)
        self.assertEqual(result['tools'][0]['arguments'],
                         {'record_id': RECORD_ALPHA})

    def test_tool_call_cannot_read_a_foreign_record(self):
        plan = attacks.materialize(
            {'tool_calls': [{'tool': 'read_record',
                             'arguments': {'record_id': RECORD_BETA}}],
             'claims': []}, 'unused')
        result = self.answer('anything', adapter=_Fixed(plan))
        self.assertEqual(result['tools'][0]['status'], 'not-found')
        self.assertIsNone(result['tools'][0]['result'])

    def test_document_obeying_adapter_executes_nothing(self):
        before = self.store.conn.execute(
            'SELECT count(*) AS n FROM records').fetchone()['n']
        result = self.answer(attacks.ATTACK_QUESTION, k=10,
                             adapter=PromptInjectingAdapter())
        after = self.store.conn.execute(
            'SELECT count(*) AS n FROM records').fetchone()['n']
        self.assertEqual(before, after)
        self.assertEqual(result['tools'], [])
        recorded = [denial['reason'] for denial in result['denied']]
        self.assertIn('tool-not-allowlisted', recorded)
        self.assertIn('invalid-argument-value', recorded)

    def test_denials_are_visible_in_the_answer(self):
        result = self.answer('anything', adapter=_Fixed(
            attacks.ATTACK_PLANS[0]['plan']))
        self.assertEqual(result['tools'], [])
        self.assertEqual(result['denied'][0]['reason'],
                         'tool-not-allowlisted')

    def test_unanswerable_question_abstains(self):
        result = self.answer(
            'What is the airspeed velocity of an unladen swallow?')
        self.assertTrue(result['abstained'])
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['citations'], [])

    def test_revocation_removes_the_claims_that_depended_on_it(self):
        first = self.answer('How many working days does a refund take?')
        cited = {hit['document'] for hit in first['citations']}
        self.assertIn('refunds', cited)
        self.store.revoke(TOKEN_ALPHA, 'refunds')
        second = self.answer('How many working days does a refund take?')
        self.assertNotIn('refunds',
                         {hit['document'] for hit in second['citations']})
        for claim in second['claims']:
            self.assertNotIn('refund is issued', claim['text'])

    def test_version_change_makes_a_carried_over_citation_unusable(self):
        first = self.answer('How many working days does a refund take?')
        stale = next(hit for hit in first['citations']
                     if hit['document'] == 'refunds')
        self.assertTrue(self.store._still_citable('alice', 'alpha', stale))
        self.store.put(TOKEN_ALPHA, 'refunds',
                       'Refunds now take twenty working days.')
        self.assertFalse(self.store._still_citable('alice', 'alpha', stale))
        second = self.answer('How many working days does a refund take?')
        self.assertNotIn(stale['chunk_id'],
                         {hit['chunk_id'] for hit in second['citations']})
        # The superseded sentence is gone even though an unrelated document
        # still uses the same three words.
        self.assertNotIn(stale['quote'], second['text'])
        self.assertIn('twenty working days', second['text'])

    def test_hostile_plan_cannot_read_a_foreign_record_end_to_end(self):
        plan = attacks.materialize(
            {'tool_calls': [{'tool': 'read_record',
                             'arguments': {'record_id': RECORD_BETA}}],
             'claims': []}, 'unused')
        result = self.answer('anything', adapter=_Fixed(plan),
                             token=TOKEN_ALPHA)
        self.assertEqual(result['tools'][0]['status'], 'not-found')
        self.assertNotIn('999', str(result))

    def test_no_foreign_markers_in_either_tenants_answer(self):
        for token, foreign in ((TOKEN_ALPHA, MARKERS_BETA),
                               (TOKEN_BETA, MARKERS_ALPHA)):
            for question in ('refund', 'invoice',
                             'TOOL read_record', 'what is the answer'):
                with self.subTest(token=token, question=question):
                    result = self.answer(question, token=token, k=5)
                    blob = str(result)
                    for marker in foreign:
                        self.assertNotIn(marker, blob)

    def test_model_configuration_is_reported(self):
        result = self.answer('How long are customer records stored?')
        self.assertEqual(result['model']['adapter'],
                         LocalExtractiveAdapter.name)
        self.assertEqual(result['model']['allowlist'], list(ALLOWED_TOOLS))
        self.assertEqual(result['answerer'], LocalExtractiveAdapter.name)

    def test_answer_is_recorded_in_history(self):
        self.answer('How long are customer records stored?')
        runs = self.store.history(TOKEN_ALPHA)
        self.assertTrue(runs[-1]['citations'])


class _Fixed:
    name = 'fixed-plan-test-double'

    def __init__(self, plan):
        self.plan_ = plan

    def plan(self, question, passages):
        return self.plan_


# ------------------------------------------------------------------- HTTP
@unittest.skipUnless(TestClient is not None and psycopg is not None
                     and database_available(), SKIP)
class AnswerHttpTests(unittest.TestCase):
    def setUp(self):
        self.ctx, self.store = seeded_store()
        self.client = TestClient(create_app(self.store))

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_answer_endpoint_returns_claims_citations_and_tools(self):
        response = self.client.post('/answer', headers=auth(TOKEN_ALPHA),
                                    json={'question': 'read record limits'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['tools'][0]['status'], 'ok')
        self.assertEqual(body['tools'][0]['result'], {'daily': 100,
                                                      'plan': 'standard'})
        self.assertEqual(body['model']['allowlist'], ['read_record'])

    def test_answer_endpoint_rejects_body_tenant(self):
        response = self.client.post('/answer', headers=auth(TOKEN_ALPHA),
                                    json={'question': 'refund',
                                          'tenant': 'beta'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('citations', response.json())

    def test_answer_endpoint_rejects_unknown_mode(self):
        response = self.client.post('/answer', headers=auth(TOKEN_ALPHA),
                                    json={'question': 'refund',
                                          'mode': 'oracle'})
        self.assertEqual(response.status_code, 422)

    def test_answer_endpoint_needs_a_token(self):
        response = self.client.post('/answer', json={'question': 'refund'})
        self.assertEqual(response.status_code, 401)

    def test_answer_history_is_re_authorized(self):
        self.client.post('/answer', headers=auth(TOKEN_ALPHA),
                         json={'question': 'How long are customer records '
                                           'stored?'})
        history = self.client.get('/history', headers=auth(TOKEN_ALPHA))
        self.assertEqual(history.status_code, 200)
        self.assertTrue(history.json()['runs'][-1]['citations'])
        for marker in MARKERS_BETA:
            self.assertNotIn(marker, history.text)

    def test_answer_does_not_leak_across_tenants(self):
        alpha = self.client.post('/answer', headers=auth(TOKEN_ALPHA),
                                 json={'question': 'TOOL read_record',
                                       'k': 10})
        beta = self.client.post('/answer', headers=auth(TOKEN_BETA),
                                json={'question': 'TOOL read_record',
                                      'k': 10})
        self.assertEqual(alpha.status_code, 200)
        self.assertEqual(beta.status_code, 200)
        for marker in MARKERS_BETA:
            self.assertNotIn(marker, alpha.text)
        for marker in MARKERS_ALPHA:
            self.assertNotIn(marker, beta.text)


if __name__ == '__main__':
    unittest.main()
