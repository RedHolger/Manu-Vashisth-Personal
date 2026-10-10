# SQL Server verification — 10 October 2026 (VERIFIED)

SqlServerDb (SQL Server OUTPUT rows, OFFSET/FETCH pagination, migration ledger,
transactional ownership transfer, update locks) plus T-SQL V1/V2 mirrors are
implemented. Databases selects the dialect by JDBC URL; DbTest and ApiTest share the
same contract across dialects. Maven test-compile passed with Microsoft JDBC 12.8.1.jre11.

Live SQL Server tests RAN 2026-10-10: 9/9 green (DbTest 6 + ApiTest 3) against
mcr.microsoft.com/mssql/server:2022-latest (linux/amd64) in Docker Desktop, disposable
`readingqueue` database. Same contract 9/9 vs PostgreSQL 16. Logs:
results/sqlserver-2026-10-10.log, results/postgres-2026-10-10.log. Full commands in
EVIDENCE.md.

Reproduce: create an isolated empty readingqueue database; set JDBC_URL to its JDBC
connection string; from backend run `mvn test -Dmigrations=../db/sqlserver`.
Tests DELETE FROM items: never point them at a real database. Keep credentials out of
committed files and shell history. Runtime: JDBC_URL selects SQL Server automatically;
Server uses matching migrations.

Notes: Apple Silicon runs the image emulated, outside Microsoft's supported x86-64
platform configuration: https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-docker-container-deployment?view=sql-server-ver16
Demo identity remains an X-User header, not production authentication. No .NET claims.
