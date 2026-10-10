-- V2 is a no-op keeper proving ordered, idempotent migration application.
CREATE TABLE IF NOT EXISTS schema_note (k TEXT PRIMARY KEY, v TEXT);
INSERT INTO schema_note(k, v) VALUES ('v2', 'status-check-already-in-v1')
ON CONFLICT (k) DO NOTHING;
