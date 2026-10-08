"""P05-01 HTTP contract: server-validated identity and cross-tenant isolation."""
import unittest

try:
    import psycopg
    from fastapi.testclient import TestClient

    from app import create_app
    from db_support import (
        DOC_ALPHA, DOC_BETA, MARKERS_ALPHA, MARKERS_BETA, RECORD_ALPHA,
        RECORD_BETA, TEXT_ALPHA, TOKEN_ALPHA, TOKEN_BETA, database_available,
        fresh_store)
except Exception as _exc:  # pragma: no cover - exercised only without the stack
    psycopg = None
    TestClient = None
    create_app = None
    database_available = fresh_store = None

SKIP = 'fastapi, httpx2 and a reachable P05 database are required'


def auth(token):
    return {'Authorization': 'Bearer %s' % token}


def body_contains(payload, markers):
    text = str(payload)
    return [marker for marker in markers if marker in text]


@unittest.skipUnless(TestClient is not None and psycopg is not None
                     and database_available(), SKIP)
class HttpContractTests(unittest.TestCase):
    def setUp(self):
        self.ctx = fresh_store()
        self.store = self.ctx.__enter__()
        self.client = TestClient(create_app(self.store))

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    # ------------------------------------------------------------- identity
    def test_health_needs_no_token(self):
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_missing_token_is_rejected(self):
        response = self.client.get('/documents/%s' % DOC_ALPHA)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(TEXT_ALPHA, response.text)

    def test_unknown_token_is_rejected(self):
        response = self.client.get('/documents/%s' % DOC_ALPHA,
                                   headers=auth('never-issued'))
        self.assertEqual(response.status_code, 401)

    def test_non_bearer_scheme_is_rejected(self):
        response = self.client.get(
            '/documents/%s' % DOC_ALPHA,
            headers={'Authorization': 'Basic %s' % TOKEN_ALPHA})
        self.assertEqual(response.status_code, 401)

    def test_body_tenant_is_rejected_on_documents(self):
        response = self.client.post(
            '/documents', headers=auth(TOKEN_ALPHA),
            json={'id': 'probe', 'text': 'probe', 'tenant': 'beta'})
        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.store.get(TOKEN_ALPHA, 'probe'))
        self.assertIsNone(self.store.get(TOKEN_BETA, 'probe'))

    def test_body_tenant_is_rejected_on_query(self):
        response = self.client.post(
            '/query', headers=auth(TOKEN_ALPHA),
            json={'question': 'refund', 'tenant': 'beta'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('citations', response.json())

    def test_matching_body_tenant_is_accepted(self):
        response = self.client.post(
            '/documents', headers=auth(TOKEN_ALPHA),
            json={'id': 'match', 'text': 'ok', 'tenant': 'alpha'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['tenant'], 'alpha')

    # ------------------------------------------------- cross-tenant retrieval
    def test_foreign_document_cannot_be_retrieved_or_downloaded(self):
        response = self.client.get('/documents/%s' % DOC_BETA,
                                   headers=auth(TOKEN_ALPHA))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body_contains(response.json(), MARKERS_BETA), [])

    def test_foreign_and_unknown_documents_are_indistinguishable(self):
        known = self.client.get('/documents/%s' % DOC_ALPHA,
                                headers=auth(TOKEN_ALPHA))
        self.assertEqual(known.status_code, 200)
        foreign = self.client.get('/documents/%s' % DOC_BETA,
                                  headers=auth(TOKEN_ALPHA))
        unknown = self.client.get('/documents/no-such-doc',
                                  headers=auth(TOKEN_ALPHA))
        self.assertEqual(foreign.status_code, unknown.status_code)
        self.assertEqual(foreign.json(), unknown.json())

    def test_same_id_in_two_tenants_does_not_collide(self):
        self.client.post('/documents', headers=auth(TOKEN_ALPHA),
                         json={'id': 'shared', 'text': 'alpha wording'})
        self.client.post('/documents', headers=auth(TOKEN_BETA),
                         json={'id': 'shared', 'text': 'beta wording'})
        alpha = self.client.get('/documents/shared', headers=auth(TOKEN_ALPHA))
        beta = self.client.get('/documents/shared', headers=auth(TOKEN_BETA))
        self.assertEqual(alpha.json()['text'], 'alpha wording')
        self.assertEqual(beta.json()['text'], 'beta wording')
        self.assertEqual(alpha.json()['tenant'], 'alpha')
        self.assertEqual(beta.json()['tenant'], 'beta')

    # ------------------------------------------------------- cross-tenant query
    def test_query_returns_only_own_citations(self):
        alpha = self.client.post('/query', headers=auth(TOKEN_ALPHA),
                                 json={'question': 'secret invoice refund'})
        beta = self.client.post('/query', headers=auth(TOKEN_BETA),
                                json={'question': 'secret invoice refund'})
        self.assertEqual(alpha.status_code, 200)
        self.assertEqual(beta.status_code, 200)
        self.assertEqual(body_contains(alpha.json(), MARKERS_BETA), [])
        self.assertEqual(body_contains(beta.json(), MARKERS_ALPHA), [])
        for citation in alpha.json()['citations']:
            self.assertNotEqual(citation['document'], DOC_BETA)
        for citation in beta.json()['citations']:
            self.assertNotEqual(citation['document'], DOC_ALPHA)

    def test_foreign_record_tool_is_not_reachable(self):
        response = self.client.get('/records/%s' % RECORD_BETA,
                                   headers=auth(TOKEN_ALPHA))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body_contains(response.json(), MARKERS_BETA), [])
        own = self.client.get('/records/%s' % RECORD_ALPHA,
                              headers=auth(TOKEN_ALPHA))
        self.assertEqual(own.status_code, 200)
        self.assertNotIn('999', own.text)

    def test_history_never_exposes_foreign_citations(self):
        self.client.post('/query', headers=auth(TOKEN_ALPHA),
                         json={'question': 'refund'})
        self.client.post('/query', headers=auth(TOKEN_BETA),
                         json={'question': 'invoice'})
        alpha = self.client.get('/history', headers=auth(TOKEN_ALPHA))
        self.assertEqual(alpha.status_code, 200)
        self.assertEqual(body_contains(alpha.json(), MARKERS_BETA), [])
        for run in alpha.json()['runs']:
            for citation in run['citations']:
                self.assertNotEqual(citation['document'], DOC_BETA)

    # ------------------------------------------------------------- happy path
    def test_authorized_flow_returns_citations(self):
        created = self.client.post('/documents', headers=auth(TOKEN_ALPHA),
                                   json={'id': 'flow', 'text': TEXT_ALPHA})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['version'], 1)
        answer = self.client.post('/query', headers=auth(TOKEN_ALPHA),
                                  json={'question': 'refunds'})
        self.assertFalse(answer.json()['abstained'])
        self.assertTrue(any(c['document'] == 'flow'
                            for c in answer.json()['citations']))

    def test_reupserting_bumps_the_version(self):
        first = self.client.post('/documents', headers=auth(TOKEN_ALPHA),
                                 json={'id': 'flow2', 'text': 'one'})
        second = self.client.post('/documents', headers=auth(TOKEN_ALPHA),
                                  json={'id': 'flow2', 'text': 'two'})
        self.assertEqual(first.json()['version'], 1)
        self.assertEqual(second.json()['version'], 2)

    def test_empty_text_is_rejected(self):
        response = self.client.post('/documents', headers=auth(TOKEN_ALPHA),
                                    json={'id': 'blank', 'text': '   '})
        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
