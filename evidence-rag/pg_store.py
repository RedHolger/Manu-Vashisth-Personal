"""PostgreSQL port of the reference Store with pgvector-ready storage.

Preserves the reference's authorization semantics: every read is filtered by the
tenant and user resolved from the session, documents are versioned with a
checksum, and a citation is only returned if it still passes the grant, version
and text recheck at answer time.

Differences from the reference, all recorded in the kit DECISIONS file:

* Document ids are unique **per tenant** (composite primary key). The reference
  uses a global primary key, which lets one tenant probe whether an id exists
  anywhere else; a tenant-scoped key makes that impossible.
* No method ever reads a row belonging to another tenant, so a cross-tenant id
  simply does not exist from the caller's point of view instead of raising.
* Document versions are shredded into persistent chunks (P05-02) with stable,
  content-derived ids. Old versions are retained like history, but every
  retrieval path joins on the current version and `finalize` re-checks the chunk
  id and its text, so a stale chunk cannot reach an answer.
 * Retrieval is available in three modes over the same membership-filtered chunk
   set: `keyword` (BM25), `vector` (pgvector cosine over local embeddings) and
   `hybrid` (reciprocal rank fusion). Candidate rankings are cached per tenant
   and question, and every write that changes visibility bumps the tenant
   generation and drops those cache rows.
 * `answer` (P05-03) runs a model adapter, then treats its plan as untrusted:
   tools are allowlisted, arguments schema-checked and claim text verified
   against the passages it cites *before* anything runs, and the single tool is
   executed with the caller's own session so no argument the model produced can
   widen authorization. Citations are re-authorized a second time at answer
   time and a claim only survives if its whole support set does.
"""
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from chunking import make_chunk_id, split_text, checksum as chunk_checksum
from embeddings import (embed, embed_one, embedding_available, vector_literal)
from model_adapter import (LocalExtractiveAdapter, model_config, supports,
                           validate_plan)
from retrieval import bm25, order_by_score, rrf_scores

MIGRATIONS_DIR = Path(__file__).resolve().parent / 'migrations'
DEFAULT_DSN = os.environ.get(
    'P05_DATABASE_URL',
    'postgresql://evidencerag:evidencerag@127.0.0.1:5435/evidencerag')

MODES = ('keyword', 'vector', 'hybrid')
MAX_CANDIDATES = 20
_TERMS = re.compile(r'\w+')


class Unauthorized(PermissionError):
    pass


class ModeUnavailable(RuntimeError):
    """A retrieval mode needs a service this deployment does not have."""


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def migrate(conn, directory=MIGRATIONS_DIR):
    """Apply every pending migration exactly once, verifying recorded checksums."""
    applied = {}
    done = []
    with conn.transaction():
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_migrations ('
            ' version TEXT PRIMARY KEY,'
            ' checksum TEXT NOT NULL,'
            ' applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        applied = {row['version']: row['checksum'] for row in conn.execute(
            'SELECT version, checksum FROM schema_migrations')}
    for path in sorted(Path(directory).glob('*.sql')):
        if path.name.startswith('.'):
            continue   # macOS AppleDouble sidecars are not migrations
        sql = path.read_text(encoding='utf-8')
        version = path.stem
        checksum = _digest(sql)
        if version in applied:
            if applied[version] != checksum:
                raise RuntimeError(
                    'migration %s changed after it was applied (recorded %s, '
                    'now %s)' % (version, applied[version], checksum))
            continue
        with conn.transaction():
            conn.execute(sql)
            conn.execute(
                'INSERT INTO schema_migrations (version, checksum) '
                'VALUES (%s, %s)', (version, checksum))
        done.append(version)
    return done


class PgStore:
    def __init__(self, dsn=DEFAULT_DSN, run_migrations=True):
        self.dsn = dsn
        self.conn = psycopg.connect(dsn, row_factory=dict_row)
        if run_migrations:
            migrate(self.conn)

    # ---------------------------------------------------------------- identity
    @contextmanager
    def _txn(self):
        with self.conn.transaction():
            yield

    def session(self, token, user, tenant):
        if not token or not user or not tenant:
            raise ValueError('nonempty identity')
        with self._txn():
            self.conn.execute(
                'INSERT INTO sessions (token_hash, user_id, tenant) '
                'VALUES (%s, %s, %s) ON CONFLICT (token_hash) DO UPDATE '
                'SET user_id = excluded.user_id, tenant = excluded.tenant',
                (_digest(token), user, tenant))

    def identity(self, token):
        with self._txn():
            row = self.conn.execute(
                'SELECT user_id, tenant FROM sessions WHERE token_hash = %s',
                (_digest(token),)).fetchone()
        if not row:
            raise Unauthorized('unknown session')
        return row['user_id'], row['tenant']

    # --------------------------------------------------------------- documents
    @staticmethod
    def _embed(texts):
        """None when the local embedding adapter is not installed, so keyword
        ingestion and every non-vector test still run on a plain system Python."""
        if not texts or not embedding_available():
            return [None] * len(texts)
        return list(embed(texts))

    @contextmanager
    def _writes(self, tenant):
        """A mutation transaction that always invalidates that tenant's cache."""
        with self._txn():
            yield
            self._invalidate(tenant)

    def _invalidate(self, tenant):
        self.conn.execute(
            'INSERT INTO tenant_generation (tenant, generation) VALUES (%s, 1) '
            'ON CONFLICT (tenant) DO UPDATE '
            'SET generation = tenant_generation.generation + 1', (tenant,))
        self.conn.execute('DELETE FROM retrieval_cache WHERE tenant = %s',
                          (tenant,))

    def put(self, token, ident, text):
        user, tenant = self.identity(token)
        if not isinstance(text, str) or not text.strip():
            raise ValueError('document text required')
        if not ident or not isinstance(ident, str):
            raise ValueError('document id required')
        # Chunking and embedding happen before the transaction opens: model
        # inference must never hold row locks.
        pieces = split_text(text)
        prepared = [{'chunk_index': index,
                     'chunk_id': make_chunk_id(tenant, ident, index, piece),
                     'text': piece,
                     'checksum': chunk_checksum(piece)}
                    for index, piece in enumerate(pieces)]
        vectors = self._embed([piece['text'] for piece in prepared])
        with self._writes(tenant):
            row = self.conn.execute(
                'SELECT version FROM documents WHERE tenant = %s AND id = %s',
                (tenant, ident)).fetchone()
            version = row['version'] + 1 if row else 1
            self.conn.execute(
                'INSERT INTO documents (tenant, id, version, text, checksum, '
                ' deleted, embedding) VALUES (%s, %s, %s, %s, %s, 0, NULL) '
                'ON CONFLICT (tenant, id) DO UPDATE SET version = '
                'excluded.version, text = excluded.text, '
                'checksum = excluded.checksum, deleted = 0, embedding = NULL',
                (tenant, ident, version, text, chunk_checksum(text)))
            self.conn.execute(
                'INSERT INTO grants (tenant, user_id, document_id) '
                'VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                (tenant, user, ident))
            self.conn.execute(
                'INSERT INTO document_versions (tenant, document_id, version, '
                'checksum, chunk_count) VALUES (%s, %s, %s, %s, %s) '
                'ON CONFLICT (tenant, document_id, version) DO NOTHING',
                (tenant, ident, version, chunk_checksum(text), len(prepared)))
            for piece, vector in zip(prepared, vectors):
                self.conn.execute(
                    'INSERT INTO chunks (tenant, document_id, version, '
                    'chunk_index, chunk_id, text, checksum, embedding) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s) '
                    'ON CONFLICT (tenant, document_id, version, chunk_index) '
                    'DO UPDATE SET chunk_id = excluded.chunk_id, '
                    'text = excluded.text, checksum = excluded.checksum, '
                    'embedding = excluded.embedding',
                    (tenant, ident, version, piece['chunk_index'],
                     piece['chunk_id'], piece['text'], piece['checksum'],
                     vector_literal(vector) if vector is not None else None))
        return version

    def _allowed(self, user, tenant, ident):
        return bool(self.conn.execute(
            'SELECT 1 FROM documents d JOIN grants g '
            '  ON d.tenant = g.tenant AND d.id = g.document_id '
            'WHERE d.tenant = %s AND d.id = %s AND d.deleted = 0 '
            '  AND g.user_id = %s',
            (tenant, ident, user)).fetchone())

    def revoke(self, token, document):
        user, tenant = self.identity(token)
        with self._writes(tenant):
            if not self._allowed(user, tenant, document):
                raise Unauthorized('not allowed')
            self.conn.execute(
                'DELETE FROM grants WHERE tenant = %s AND user_id = %s '
                'AND document_id = %s', (tenant, user, document))

    def delete(self, token, document):
        user, tenant = self.identity(token)
        with self._writes(tenant):
            if not self._allowed(user, tenant, document):
                raise Unauthorized('not allowed')
            self.conn.execute(
                'UPDATE documents SET deleted = 1 WHERE tenant = %s AND id = %s',
                (tenant, document))

    def get(self, token, ident):
        """Retrieve one document. Unknown ids and foreign ids are indistinguishable."""
        user, tenant = self.identity(token)
        with self._txn():
            if not self._allowed(user, tenant, ident):
                return None
            row = self.conn.execute(
                'SELECT id, tenant, version, text, checksum FROM documents '
                'WHERE tenant = %s AND id = %s AND deleted = 0',
                (tenant, ident)).fetchone()
        return dict(row) if row else None

    # ---------------------------------------------------------------- retrieval
    @staticmethod
    def _question_hash(question):
        return hashlib.sha256(question.encode('utf-8')).hexdigest()

    @staticmethod
    def _hit(row, score):
        return {'document': row['document_id'],
                'version': row['version'],
                'chunk': row['chunk_index'],
                'chunk_id': row['chunk_id'],
                'quote': row['text'],
                'score': float(score)}

    def _generation(self, tenant):
        row = self.conn.execute(
            'SELECT generation FROM tenant_generation WHERE tenant = %s',
            (tenant,)).fetchone()
        return int(row['generation']) if row else 0

    def _cache_get(self, tenant, user, question, mode, generation):
        row = self.conn.execute(
            'SELECT hits FROM retrieval_cache '
            'WHERE tenant = %s AND user_id = %s AND question_hash = %s AND mode = %s '
            'AND generation = %s',
            (tenant, user, self._question_hash(question), mode,
             generation)).fetchone()
        return row['hits'] if row else None   # jsonb already decodes to a list

    def _cache_put(self, tenant, user, question, mode, generation, hits):
        self.conn.execute(
            'INSERT INTO retrieval_cache '
            '(tenant, user_id, question_hash, mode, generation, hits) '
            'VALUES (%s, %s, %s, %s, %s, %s) '
            'ON CONFLICT (tenant, user_id, question_hash, mode) DO UPDATE '
            'SET generation = excluded.generation, hits = excluded.hits',
            (tenant, user, self._question_hash(question), mode, generation,
             json.dumps(hits)))

    def _visible_chunks(self, user, tenant):
        """Current-version chunks this user may read; membership filtered."""
        rows = self.conn.execute(
            'SELECT c.document_id, c.version, c.chunk_index, c.chunk_id, c.text, '
            '       c.embedding IS NOT NULL AS embedded '
            'FROM chunks c '
            'JOIN documents d ON d.tenant = c.tenant AND d.id = c.document_id '
            'JOIN grants g ON g.tenant = d.tenant AND g.document_id = d.id '
            'WHERE c.tenant = %s AND g.user_id = %s AND d.deleted = 0 '
            '  AND c.version = d.version '
            'ORDER BY c.document_id, c.chunk_index',
            (tenant, user)).fetchall()
        return [{'document_id': row['document_id'],
                 'version': row['version'],
                 'chunk_index': row['chunk_index'],
                 'chunk_id': row['chunk_id'],
                 'text': row['text'],
                 'embedded': row['embedded'],
                 'terms': _TERMS.findall(row['text'].lower())}
                for row in rows]

    @staticmethod
    def _rank_keyword(question, chunks, limit):
        scores = bm25(question, chunks)
        by_id = {chunk['chunk_id']: chunk for chunk in chunks}
        return [PgStore._hit(by_id[chunk_id], scores[chunk_id])
                for chunk_id in order_by_score(scores, limit)]

    def _rank_vector(self, tenant, user, query_literal, limit):
        rows = self.conn.execute(
            'SELECT c.document_id, c.version, c.chunk_index, c.chunk_id, c.text, '
            '       1 - (c.embedding <=> %s::vector) AS score '
            'FROM chunks c '
            'JOIN documents d ON d.tenant = c.tenant AND d.id = c.document_id '
            'JOIN grants g ON g.tenant = d.tenant AND g.document_id = d.id '
            'WHERE c.tenant = %s AND g.user_id = %s AND d.deleted = 0 '
            '  AND c.version = d.version AND c.embedding IS NOT NULL '
            'ORDER BY c.embedding <=> %s::vector, c.document_id, c.chunk_index '
            'LIMIT %s',
            (query_literal, tenant, user, query_literal, limit)).fetchall()
        return [self._hit(row, row['score']) for row in rows]

    @staticmethod
    def _rank_hybrid(keyword_hits, vector_hits, limit):
        scores = rrf_scores([[hit['chunk_id'] for hit in keyword_hits],
                             [hit['chunk_id'] for hit in vector_hits]])
        by_id = {hit['chunk_id']: hit
                 for hit in list(keyword_hits) + list(vector_hits)}
        return [dict(by_id[chunk_id], score=scores[chunk_id])
                for chunk_id in order_by_score(scores, limit)]

    def candidates(self, token, question, k=3, mode='keyword'):
        """Rank the chunks this user may read, optionally from the cache."""
        if k < 1 or k > 20:
            raise ValueError('invalid k')
        if mode not in MODES:
            raise ValueError('invalid mode %r; expected one of %s'
                             % (mode, ', '.join(MODES)))
        if not isinstance(question, str) or not question.strip():
            raise ValueError('question required')
        user, tenant = self.identity(token)
        query_literal = None
        if mode in ('vector', 'hybrid'):
            if not embedding_available():
                raise ModeUnavailable(
                    'vector retrieval needs the local embedding adapter; '
                    'install requirements.txt into .venv')
            query_literal = vector_literal(embed_one(question))
        with self._txn():
            generation = self._generation(tenant)
            hits = self._cache_get(tenant, user, question, mode, generation)
            if hits is None:
                chunks = self._visible_chunks(user, tenant)
                if mode == 'keyword':
                    hits = self._rank_keyword(question, chunks,
                                              MAX_CANDIDATES)
                elif mode == 'vector':
                    hits = self._rank_vector(tenant, user, query_literal,
                                             MAX_CANDIDATES)
                else:
                    keyword_hits = self._rank_keyword(question, chunks,
                                                      MAX_CANDIDATES)
                    vector_hits = self._rank_vector(tenant, user,
                                                    query_literal,
                                                    MAX_CANDIDATES)
                    hits = self._rank_hybrid(keyword_hits, vector_hits,
                                             MAX_CANDIDATES)
                self._cache_put(tenant, user, question, mode, generation, hits)
            # Validate cached passages before any model adapter can inspect them.
            hits = [hit for hit in hits if self._still_citable(user, tenant, hit)]
        return hits[:k]

    def _still_citable(self, user, tenant, hit):
        """Grant, deletion, version, chunk id and chunk text must all still hold."""
        if not self._allowed(user, tenant, hit['document']):
            return False
        row = self.conn.execute(
            'SELECT version FROM documents WHERE tenant = %s AND id = %s',
            (tenant, hit['document'])).fetchone()
        if not row or row['version'] != hit['version']:
            return False
        chunk = self.conn.execute(
            'SELECT 1 FROM chunks WHERE tenant = %s AND document_id = %s '
            'AND version = %s AND chunk_index = %s AND chunk_id = %s '
            'AND text = %s',
            (tenant, hit['document'], hit['version'], hit['chunk'],
             hit.get('chunk_id'), hit['quote'])).fetchone()
        return chunk is not None

    def finalize(self, token, question, hits, mode='keyword'):
        """Re-authorize every citation immediately before it is returned."""
        user, tenant = self.identity(token)
        with self._txn():
            safe = [hit for hit in hits
                    if self._still_citable(user, tenant, hit)]
            answer = {
                'abstained': not safe,
                'mode': mode,
                'answerer': 'extractive',
                'citations': safe,
                'text': '\n'.join(hit['quote'] for hit in safe) if safe
                        else 'No authorized supporting passage found.',
            }
            self.conn.execute(
                'INSERT INTO query_runs (user_id, tenant, question, answer) '
                'VALUES (%s, %s, %s, %s)',
                (user, tenant, question, json.dumps(answer)))
        return answer

    def query(self, token, question, k=3, mode='keyword'):
        return self.finalize(token, question,
                             self.candidates(token, question, k, mode), mode)

    # ----------------------------------------------------------------- answer
    def execute_tool(self, token, call):
        """Run one validated call with the *caller's* session, never the model's.

        The model supplies arguments; it never supplies identity. `read_record`
        re-resolves the tenant from the bearer token, so a record id belonging
        to another tenant is simply not there. The store also refuses any tool
        it does not implement, so a validator bug cannot become an execution.
        """
        name, arguments = call['tool'], call['arguments']
        if name != 'read_record':
            return {'tool': name, 'arguments': dict(arguments),
                    'status': 'denied', 'result': None}
        value = self.read_record(token, arguments['record_id'])
        return {'tool': name, 'arguments': dict(arguments),
                'status': 'ok' if value is not None else 'not-found',
                'result': value}

    def answer(self, token, question, k=3, mode='keyword', adapter=None):
        """Retrieve, let a model plan, validate the plan, then re-authorize.

        Order matters: the plan is built from the retriever's candidates, every
        claim is checked against the text of the chunks it cites, the tool runs
        under the caller's identity, and only then are citations re-checked
        against grant, deletion, version, chunk id and chunk text. A claim whose
        support does not survive in full is dropped, so the returned citations
        are exactly the evidence the answer still stands on.
        """
        adapter = adapter or LocalExtractiveAdapter()
        user, tenant = self.identity(token)
        hits = self.candidates(token, question, k, mode)
        calls, claims, denied = validate_plan(adapter.plan(question, hits), hits)
        tools = [self.execute_tool(token, call) for call in calls]
        with self._txn():
            safe = [hit for hit in hits
                    if self._still_citable(user, tenant, hit)]
        safe_by_id = {hit['chunk_id']: hit for hit in safe}

        kept = []
        for claim in claims:
            surviving = [chunk_id for chunk_id in claim['support']
                         if chunk_id in safe_by_id]
            if not surviving:
                continue
            quotes = [safe_by_id[chunk_id]['quote'] for chunk_id in surviving]
            if not supports(claim['text'], quotes):
                continue   # the passage it leaned on no longer says this
            kept.append({'text': claim['text'], 'support': surviving})
        used = list(dict.fromkeys(chunk_id for claim in kept
                                  for chunk_id in claim['support']))
        answer = {
            'abstained': not kept,
            'mode': mode,
            'answerer': adapter.name,
            'model': model_config(adapter),
            'claims': kept,
            'citations': [safe_by_id[chunk_id] for chunk_id in used],
            'text': '\n'.join(claim['text'] for claim in kept) if kept
                    else 'No authorized supporting passage found.',
            'tools': tools,
            'denied': denied,
        }
        with self._txn():
            self.conn.execute(
                'INSERT INTO query_runs (user_id, tenant, question, answer) '
                'VALUES (%s, %s, %s, %s)',
                (user, tenant, question, json.dumps(answer)))
        return answer

    # --------------------------------------------------------------- tool/read
    def read_record(self, token, record_id):
        _, tenant = self.identity(token)
        with self._txn():
            row = self.conn.execute(
                'SELECT value FROM records WHERE tenant = %s AND id = %s',
                (tenant, record_id)).fetchone()
        return json.loads(row['value']) if row else None

    def put_record(self, tenant, record_id, value):
        """Seeding only; there is no HTTP route that writes records."""
        with self._txn():
            self.conn.execute(
                'INSERT INTO records (tenant, id, value) VALUES (%s, %s, %s) '
                'ON CONFLICT (tenant, id) DO UPDATE SET value = excluded.value',
                (tenant, record_id, json.dumps(value)))

    def history(self, token):
        """Re-authorize every historical answer; never return stored text blindly."""
        user, tenant = self.identity(token)
        result = []
        with self._txn():
            runs = self.conn.execute(
                'SELECT id, answer FROM query_runs '
                'WHERE tenant = %s AND user_id = %s ORDER BY id',
                (tenant, user)).fetchall()
            for run in runs:
                answer = json.loads(run['answer'])
                permitted = [hit for hit in answer['citations']
                             if self._still_citable(user, tenant, hit)]
                result.append({'id': run['id'], 'citations': permitted})
        return result

    def close(self):
        self.conn.close()
