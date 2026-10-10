# ReadingQueue — requirements map

| Requirement (BUILD_PROMPTS tsql) | Check | Result |
|---|---|---|
| Java REST backend | JDK HttpServer + JDBC; 9 JUnit tests vs real PG16 | pass |
| SQL Server/T-SQL adapter | T-SQL V1/V2 mirrors written, dialect diffs documented | scripts only |
| PostgreSQL option | pgjdbc impl; migrations applied + ordered + idempotent | pass |
| Search/ownership/migrations/pagination | DbTest + ApiTest cases | pass |
| Real T-SQL txn/ownership/query tests | no SQL Server available | UNRUN (SETUP_SQLSERVER.md) |
| No invented .NET experience | nothing .NET anywhere | clean |
| React reading-list UI | tsc + vite build; 2 TS rule tests | pass |
