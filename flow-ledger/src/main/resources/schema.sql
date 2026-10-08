CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY,
  idempotency_key TEXT UNIQUE NOT NULL,
  body_hash TEXT NOT NULL,
  type TEXT NOT NULL,
  payload JSONB,
  status TEXT NOT NULL DEFAULT 'PENDING',
  result JSONB,
  lease_owner TEXT,
  lease_expiry TIMESTAMPTZ,
  lease_generation BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attempts (
  id BIGSERIAL PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id),
  attempt_no INT NOT NULL,
  owner TEXT NOT NULL,
  generation BIGINT NOT NULL,
  outcome TEXT NOT NULL DEFAULT 'STARTED',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS results (
  job_id UUID PRIMARY KEY REFERENCES jobs(id),
  output JSONB NOT NULL,
  committed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outbox_events (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id),
  type TEXT NOT NULL,
  payload JSONB NOT NULL,
  dispatched BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS downstream_effects (
  dedup_key TEXT PRIMARY KEY,
  job_id UUID NOT NULL,
  output JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consumer_seen (
  event_id UUID PRIMARY KEY,
  seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
