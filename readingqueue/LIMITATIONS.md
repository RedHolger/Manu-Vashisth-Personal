# ReadingQueue — LIMITATIONS (updated 10 October 2026)

Resolved: live SQL Server tests now RUN and green (9/9 on SQL Server 2022, linux/amd64
via Docker Desktop; same contract 9/9 on PostgreSQL 16). See EVIDENCE.md and
results/sqlserver-2026-10-10.log + results/postgres-2026-10-10.log.

Remaining honest boundaries:
- SQL Server ran emulated (linux/amd64 on Apple Silicon), outside Microsoft's supported
  x86-64 platform configuration: https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-docker-container-deployment?view=sql-server-ver16
- Demo identity remains an X-User header, not production authentication.
- T-SQL verified; no .NET/C# claims (C# gap stays in role 07 notes).
- Tests run against a disposable `readingqueue` test database and TRUNCATE/DELETE its
  items table: never point them at a real database. Credentials stay out of committed files.

To reproduce on a suitable SQL Server test instance: create an isolated empty readingqueue
database; set JDBC_URL to its JDBC connection string; from backend run
`mvn test -Dmigrations=../db/sqlserver`. Passing PostgreSQL tests is not SQL Server
verification — both were run here.
