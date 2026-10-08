-- 0001_init.sql — P05-01 storage schema.
--
-- Tenant is a column on every table and is always supplied by the server from
-- the authenticated session, never by the request body. Document ids are unique
-- per tenant (composite primary key), so one tenant cannot observe whether an
-- id exists in another tenant.
--
-- `embedding` is declared now so the pgvector extension and the target
-- dimension are fixed by the schema; it stays NULL until P05-02 fills it.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    tenant     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    tenant    TEXT        NOT NULL,
    id        TEXT        NOT NULL,
    version   INTEGER     NOT NULL,
    text      TEXT        NOT NULL,
    checksum  TEXT        NOT NULL,
    deleted   INTEGER     NOT NULL DEFAULT 0,
    embedding vector(384),
    PRIMARY KEY (tenant, id)
);

CREATE TABLE IF NOT EXISTS grants (
    tenant      TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    document_id TEXT NOT NULL,
    PRIMARY KEY (tenant, user_id, document_id),
    FOREIGN KEY (tenant, document_id) REFERENCES documents (tenant, id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS records (
    tenant TEXT NOT NULL,
    id     TEXT NOT NULL,
    value  TEXT NOT NULL,
    PRIMARY KEY (tenant, id)
);

CREATE TABLE IF NOT EXISTS query_runs (
    id       BIGSERIAL PRIMARY KEY,
    user_id  TEXT NOT NULL,
    tenant   TEXT NOT NULL,
    question TEXT NOT NULL,
    answer   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS documents_live_lookup
    ON documents (tenant) WHERE deleted = 0;
CREATE INDEX IF NOT EXISTS query_runs_by_actor
    ON query_runs (tenant, user_id);
