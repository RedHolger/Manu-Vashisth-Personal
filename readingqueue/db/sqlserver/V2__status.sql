-- T-SQL mirror of V2 keeper. Verified 2026-10-10 vs SQL Server 2022.
IF OBJECT_ID('schema_note', 'U') IS NULL
  CREATE TABLE schema_note (k NVARCHAR(128) PRIMARY KEY, v NVARCHAR(512));
IF NOT EXISTS (SELECT 1 FROM schema_note WHERE k = 'v2')
  INSERT INTO schema_note(k, v) VALUES ('v2', 'status-check-already-in-v1');
