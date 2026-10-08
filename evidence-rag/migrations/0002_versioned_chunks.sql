-- P05-02: versioned chunks with stable ids, plus a generation-invalidated
-- retrieval cache. Old versions are retained as history the way query_runs is;
-- every retrieval path filters on the current version and finalize() re-checks
-- the chunk id, so retention cannot leak stale text into an answer.

CREATE TABLE IF NOT EXISTS document_versions (
    tenant       TEXT        NOT NULL,
    document_id  TEXT        NOT NULL,
    version      INTEGER     NOT NULL,
    checksum     TEXT        NOT NULL,
    chunk_count  INTEGER     NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant, document_id, version),
    FOREIGN KEY (tenant, document_id)
        REFERENCES documents (tenant, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    tenant       TEXT    NOT NULL,
    document_id  TEXT    NOT NULL,
    version      INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    chunk_id     TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    checksum     TEXT    NOT NULL,
    embedding    vector(384),
    PRIMARY KEY (tenant, document_id, version, chunk_index),
    FOREIGN KEY (tenant, document_id, version)
        REFERENCES document_versions (tenant, document_id, version)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS chunks_current_idx
    ON chunks (tenant, document_id, version);

-- One row per tenant: bumped by every write that can change what a query may
-- see, so a cached ranking can be recognized as stale by comparing generations.
CREATE TABLE IF NOT EXISTS tenant_generation (
    tenant      TEXT  PRIMARY KEY,
    generation  BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS retrieval_cache (
    tenant         TEXT   NOT NULL,
    question_hash  TEXT   NOT NULL,
    mode           TEXT   NOT NULL,
    generation     BIGINT NOT NULL,
    hits           JSONB  NOT NULL,
    PRIMARY KEY (tenant, question_hash, mode)
);
