# ReadingQueue — SPEC (Milestone 1)

Scope: Java REST reading-list backend with dual-dialect migrations, for role 07
(Rakuten Kobo: T-SQL requested). Local PostgreSQL 16 and SQL Server 2022
(Docker, linux/amd64) both run the real 9-test contract; see EVIDENCE.md.

## Domain

Reading-list items: id, owner, title, url, status (unread/reading/done),
created_at. Rules: users mutate only their own items (ownership 403);
search matches title case-insensitively with pagination (limit ≤ 50);
ownership transfer runs in a transaction (rollback on forced error).

## Components

- `backend/` Maven (Java 17+, JDK HttpServer, JDBC, pgjdbc 42.7.5, JUnit 5):
  routes GET /api/items?search=&page=, POST /api/items, PATCH
  /api/items/{id}, DELETE /api/items/{id}, POST /api/items/{id}/transfer.
  `X-User` header = identity (demo auth, stated).
- `db/postgres/V1__init.sql`, `V2__status.sql` — applied by `Migrator` in order
  (checksums recorded); `db/sqlserver/` mirrors in T-SQL (IDENTITY, NVARCHAR,
  DATETIME2, same semantics) — executed 2026-10-10 vs SQL Server 2022 (9/9).
- `ui/` React+TS reading-list (list/search/add/status/delete, user switcher).

## Acceptance mapping

Real Postgres AND SQL Server tests: transaction rollback, ownership 403, search, pagination,
migration order/idempotence (same contract, both dialects 9/9). UI builds (tsc + vite). No .NET claims anywhere.
