# ReadingQueue — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64; OpenJDK 25.0.2, Maven (Central reachable), local
PostgreSQL 16 (initdb cluster, port 55433); Node v22.12.0, Vite 5.4.21,
React 18.3.1, TS 5.6.3.

## Commands (exit 0)

- `./pg.sh` → `mvn test`: 9/9 JUnit OK (DbTest 6: migration order/idempotence,
  ownership 403s, search/pagination caps, transfer commit, rollback-on-hook,
  validation; ApiTest 3: CRUD round-trip, HTTP 403s, codes/caps).
- `./demo.sh` → 201/200/403/transfer-200/verified transcript.
- UI: `node --experimental-strip-types --test "tests/*.test.ts"` 2/2 OK;
  `npm run build` tsc + vite green.

## Measured behavior

- Transfer rollback: forced mid-transaction failure leaves owner unchanged.
- Ownership: cross-user PATCH/DELETE → 403 at service AND HTTP layers.
- Migrations V1+V2 applied in order, checksummed, re-runnable no-op.

## Claim basis for CV 07 (role 07 only, partial gap)

- "Built a Java REST reading-list backend on PostgreSQL with ordered,
  checksummed migrations, ownership checks, search/pagination and a
  transaction rollback test (9 JUnit tests green), plus a React UI."
- "T-SQL migration mirrors written; live SQL Server tests UNRUN (no server).
  No .NET claims." (t-sql gap stays open in role notes.)

# SQL Server adapter — 10 October 2026

Implemented SqlServerDb with SQL Server OUTPUT rows, OFFSET/FETCH pagination, migration ledger, transactional ownership transfer and update locks. Databases selects the dialect by JDBC URL; DbTest and ApiTest now share the same contract across dialects. Maven test-compile passed with Microsoft JDBC 12.8.1.jre11.

Live SQL Server tests remain UNRUN. Docker is running, but `docker pull --platform linux/amd64 mcr.microsoft.com/mssql/server:2022-latest` failed with containerd input/output error; the internal drive had 203 MiB available. No user data was deleted. This Apple Silicon host also requires emulation, outside Microsoft's supported x86-64 platform configuration: https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-docker-container-deployment?view=sql-server-ver16

To verify on a suitable SQL Server test instance: create an isolated empty readingqueue database; set JDBC_URL to its JDBC connection string; from backend run `mvn test -Dmigrations=../db/sqlserver`. Tests TRUNCATE items: never point them at a real database. Keep credentials out of committed files and shell history. Runtime: JDBC_URL selects SQL Server automatically; Server uses matching migrations. Passing PostgreSQL tests is not SQL Server verification.

Demo identity remains an X-User header, not production authentication. No .NET claims.

# SQL Server verification — 10 October 2026 (measured)

Environment: macOS arm64; Docker Desktop 4.43.1, Engine 28.3.0;
image mcr.microsoft.com/mssql/server:2022-latest (linux/amd64, emulated);
local PostgreSQL 16 (port 55433); OpenJDK 25.0.2, Maven; Microsoft JDBC 12.8.1.jre11.

Container (disposable test instance, no user data):
- `docker pull --platform linux/amd64 mcr.microsoft.com/mssql/server:2022-latest` → exit 0.
- `docker run -d --platform linux/amd64 --name rq-sqlserver -e ACCEPT_EULA=Y -e MSSQL_SA_PASSWORD='…' -p 14333:1433 <image>` → exit 0.
- `sqlcmd -S localhost -U sa -C -Q "…CREATE DATABASE readingqueue…"` → readingqueue listed.

Code fixes required by the live run (both kept, Postgres re-verified):
- Tests used `TRUNCATE items` (PostgreSQL-only syntax); changed to `DELETE FROM items`
  in DbTest.java and ApiTest.java — works on both dialects.
- SqlServerDb.migrate split files on `;`, which fragmented `--` comment lines containing
  `;` (V1 header) into invalid statements ("Incorrect syntax near '.'"); migrator now
  strips full-line `--` comments before splitting.

Commands (exit 0, same 9-test contract both dialects):
- `mvn -f backend/pom.xml test -DjdbcUrl="jdbc:postgresql://127.0.0.1:55433/readingqueue" -Dmigrations="<abs>/db/postgres"` → Tests run: 9, Failures: 0, Errors: 0 (DbTest 6, ApiTest 3). Log: results/postgres-2026-10-10.log.
- `mvn test -DjdbcUrl="jdbc:sqlserver://127.0.0.1:14333;databaseName=readingqueue;…;encrypt=false;loginTimeout=30" -Dmigrations="../db/sqlserver"` (from backend/) → Tests run: 9, Failures: 0, Errors: 0 (DbTest 6, ApiTest 3). Log: results/sqlserver-2026-10-10.log.
- `./pg.sh` (lifecycle initdb/start/test/stop) → exit 0. Log: results/pg-2026-10-10.log.

Claim basis for CV 07 (role 07): "Built a Java REST reading-list backend with ordered,
checksummed migrations, ownership checks, search/pagination and a transaction rollback
test — same 9-test contract green on PostgreSQL 16 and SQL Server 2022 — plus a React UI."
T-SQL gap closed; C#/.NET still correctly absent (role notes).
