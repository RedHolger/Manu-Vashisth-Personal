CREATE TABLE items (
  id SERIAL PRIMARY KEY,
  owner TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'unread' CHECK (status IN ('unread','reading','done')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX items_owner_idx ON items(owner);
