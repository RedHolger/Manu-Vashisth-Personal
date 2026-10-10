# ReadingQueue — Java REST reading list, dual-dialect migrations (role 07)

PostgreSQL 16 + SQL Server 2022 backends (both 9/9 green 2026-10-10) + React UI.
See EVIDENCE.md for measured runs, LIMITATIONS.md for the honest boundary.

## Setup

- Backend tests (needs local PostgreSQL 16): `./pg.sh` (initdb/start/test/stop).
- SQL Server tests (needs Docker): start `rq-sqlserver` per EVIDENCE.md, then from
  `backend/`: `mvn test -DjdbcUrl="jdbc:sqlserver://127.0.0.1:14333;databaseName=readingqueue;user=sa;password=…;encrypt=false" -Dmigrations="../db/sqlserver"`.
- UI: `cd ui && npm install && npm run build`; TS tests:
  `node --experimental-strip-types --test "tests/*.test.ts"`.
- Demo: `./demo.sh` (PG + backend + API transcript → results/demo.json).
- SQL Server path: see SETUP_SQLSERVER.md (needs Docker — UNRUN here).

## Layout

- `SPEC.md`, `SETUP_SQLSERVER.md`.
- `backend/` (Maven Java 17: Db interface, PostgresDb, Migrator-in-Db, Server;
  JUnit DbTest 6 + ApiTest 3).
- `db/postgres/` (V1/V2, executed) + `db/sqlserver/` (T-SQL mirrors, executed 2026-10-10).
- `ui/` (React+TS reading list; rules.test.ts).
- `demo_api.py`/`demo.sh`, `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
