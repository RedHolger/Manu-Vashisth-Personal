-- T-SQL mirror of V1 (Postgres-tested semantics). Verified 2026-10-10 vs SQL Server 2022.
-- Diff from Postgres: IDENTITY instead of SERIAL, NVARCHAR instead of TEXT, DATETIME2/SYSDATETIME.
CREATE TABLE items (
  id INT IDENTITY(1,1) PRIMARY KEY,
  owner NVARCHAR(128) NOT NULL,
  title NVARCHAR(512) NOT NULL,
  url NVARCHAR(1024) NOT NULL DEFAULT '',
  status NVARCHAR(16) NOT NULL DEFAULT 'unread'
    CHECK (status IN ('unread','reading','done')),
  created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
CREATE INDEX items_owner_idx ON items(owner);
