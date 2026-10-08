"""FastAPI transport for the P05 store.

Identity is always resolved server-side from `Authorization: Bearer <token>` by
looking the token up in `sessions`. The request body may not assert a tenant:
the models accept an optional `tenant` only so a mismatch can be rejected with an
explicit error instead of being silently ignored.

Endpoints
    GET  /health                liveness
    POST /documents             {id, text, tenant?}                 -> 201
    GET  /documents/{id}        retrieve / download one document    -> 200 | 404
    POST /query                 {question, k?, mode?, tenant?}      -> 200 | 503
    POST /answer                {question, k?, mode?, tenant?}      -> 200 | 503
    GET  /records/{id}          the one read-only structured tool   -> 200 | 404
    GET  /history               re-authorized citations             -> 200

`mode` selects the ranking: keyword (BM25, the default), vector (pgvector cosine
over local 384-dimension embeddings) or hybrid (reciprocal rank fusion of the
two). A mode whose adapter is not installed returns 503 rather than silently
falling back to keyword results.

`/answer` additionally runs the model adapter over the same candidates. The
plan it returns is untrusted input: tools are allowlisted, arguments are
schema-checked, claim text has to appear in the passages it cites, and the one
allowlisted tool is executed with this request's session. The response carries
the claims, exactly the citations that currently support them, any tool results
and every rejection the validator made.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from pg_store import DEFAULT_DSN, MODES, PgStore, ModeUnavailable, Unauthorized

_bearer = HTTPBearer(auto_error=False)


class DocumentIn(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    text: str = Field(min_length=1)
    tenant: Optional[str] = None


class QueryIn(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    k: int = Field(default=3, ge=1, le=20)
    mode: str = Field(default='keyword')
    tenant: Optional[str] = None


class AnswerIn(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    k: int = Field(default=3, ge=1, le=20)
    mode: str = Field(default='keyword')
    tenant: Optional[str] = None


@dataclass(frozen=True)
class Identity:
    user: str
    tenant: str
    token: str


def _reject_claimed_tenant(claimed: Optional[str], actor: Identity):
    """Reject a body-supplied tenant instead of trusting or silently dropping it."""
    if claimed is not None and claimed != actor.tenant:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='tenant is derived from the bearer token, not the request '
                   'body (token tenant %r, body said %r)'
                   % (actor.tenant, claimed))


def create_app(store: PgStore) -> FastAPI:
    app = FastAPI(title='EvidenceRAG', version='0.1.0',
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store

    def identity(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    ) -> Identity:
        if credentials is None or (credentials.scheme or '').lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='bearer token required',
                headers={'WWW-Authenticate': 'Bearer'})
        try:
            user, tenant = store.identity(credentials.credentials)
        except Unauthorized:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='unknown session',
                headers={'WWW-Authenticate': 'Bearer'})
        return Identity(user=user, tenant=tenant,
                        token=credentials.credentials)

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.post('/documents', status_code=status.HTTP_201_CREATED)
    def put_document(payload: DocumentIn, actor: Identity = Depends(identity)):
        _reject_claimed_tenant(payload.tenant, actor)
        try:
            version = store.put(actor.token, payload.id, payload.text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        stored = store.get(actor.token, payload.id)
        return {'id': payload.id, 'tenant': actor.tenant, 'version': version,
                'checksum': stored['checksum'] if stored else None}

    @app.get('/documents/{document_id}')
    def get_document(document_id: str, actor: Identity = Depends(identity)):
        document = store.get(actor.token, document_id)
        if document is None:
            # Unknown and unauthorized share a status so a caller cannot probe
            # another tenant for the existence of an id.
            raise HTTPException(status_code=404, detail='not found')
        return document

    @app.post('/query')
    def query(payload: QueryIn, actor: Identity = Depends(identity)):
        _reject_claimed_tenant(payload.tenant, actor)
        if payload.mode not in MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail='mode must be one of %s' % ', '.join(MODES))
        try:
            return store.query(actor.token, payload.question, k=payload.k,
                               mode=payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except ModeUnavailable as exc:
            # The request is fine; this deployment lacks the adapter.
            raise HTTPException(status_code=503, detail=str(exc))

    @app.post('/answer')
    def answer(payload: AnswerIn, actor: Identity = Depends(identity)):
        _reject_claimed_tenant(payload.tenant, actor)
        if payload.mode not in MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail='mode must be one of %s' % ', '.join(MODES))
        try:
            return store.answer(actor.token, payload.question, k=payload.k,
                                mode=payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except ModeUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @app.get('/records/{record_id}')
    def read_record(record_id: str, actor: Identity = Depends(identity)):
        value = store.read_record(actor.token, record_id)
        if value is None:
            raise HTTPException(status_code=404, detail='not found')
        return {'id': record_id, 'tenant': actor.tenant, 'value': value}

    @app.get('/history')
    def history(actor: Identity = Depends(identity)):
        return {'runs': store.history(actor.token)}

    return app


def create_app_from_env(dsn: str = DEFAULT_DSN) -> FastAPI:
    return create_app(PgStore(dsn))
