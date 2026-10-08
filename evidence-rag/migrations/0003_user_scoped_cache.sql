-- Old tenant-wide cache entries have no user and cannot match a valid session.
-- Keep them until the normal tenant invalidation rather than assigning ownership.
ALTER TABLE retrieval_cache ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE retrieval_cache DROP CONSTRAINT retrieval_cache_pkey;
ALTER TABLE retrieval_cache ADD PRIMARY KEY (tenant, user_id, question_hash, mode);
