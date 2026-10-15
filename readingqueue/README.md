# ReadingQueue — Dual-Dialect SQL & Java 17 REST Engine

[![Live Demo](https://img.shields.io/badge/Live%20Demo-readingqueue--demo.vercel.app-4f46e5?style=for-the-badge&logo=vercel&logoColor=white)](https://readingqueue-demo.vercel.app)
[![Contract](https://img.shields.io/badge/JUnit%205-9%2F9%20Green-10b981?style=for-the-badge&logo=junit5&logoColor=white)](https://readingqueue-demo.vercel.app)
[![Dialects](https://img.shields.io/badge/Databases-PostgreSQL%2016%20%7C%20SQL%20Server%202022-0ea5e9?style=for-the-badge&logo=postgresql&logoColor=white)](https://readingqueue-demo.vercel.app)

> **Live Interactive Application**: **[https://readingqueue-demo.vercel.app](https://readingqueue-demo.vercel.app)**
> 
> Explore the live Linear/Kestra-grade dashboard: test row-level ownership security (403 enforcement), execute atomic ownership transfers with injected mid-transaction fault simulations (verifying ACID rollback), inspect dual-dialect SQL queries side-by-side, and run automated verification contracts interactively in your browser.

---

## Architecture Overview

ReadingQueue is a zero-dependency Java 17 REST microservice and React frontend designed to solve dual-dialect enterprise database portability across **PostgreSQL 16** and **Microsoft SQL Server 2022 (T-SQL)** under identical test contracts.

```
                  +----------------------------------------------+
                  |         Linear-Inspired React 18 UI          |
                  |  - Role & identity switcher (Alice / Bob)    |
                  |  - Interactive ACID transaction visualizer   |
                  |  - Dual-dialect SQL syntax inspector         |
                  +----------------------+-----------------------+
                                         | HTTP / JSON (X-User Auth)
                                         v
                  +----------------------------------------------+
                  |            Java 17 Server (JDK)              |
                  |  - Zero-framework HttpServer (no Spring/ORM) |
                  |  - Explicit route dispatcher & 403 barriers  |
                  +----------------------+-----------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |           Db Interface (Contract)            |
                  +----------------------+-----------------------+
                                         |
               +-------------------------+-------------------------+
               | (jdbc:postgresql:)                                | (jdbc:sqlserver:)
               v                                                   v
  +---------------------------+                       +---------------------------+
  |      PostgresDb.java      |                       |     SqlServerDb.java      |
  | - BIGSERIAL primary keys  |                       | - BIGINT IDENTITY(1,1)    |
  | - RETURNING clause        |                       | - OUTPUT INSERTED.*       |
  | - LIMIT / OFFSET paging   |                       | - OFFSET / FETCH paging   |
  | - FOR UPDATE row lock     |                       | - WITH (UPDLOCK, ROWLOCK) |
  +---------------------------+                       +---------------------------+
```

---

## Key Capabilities

### 1. Row-Level Ownership Enforcement (HTTP 403 Forbidden)
- Items are strictly owned by their creator (`owner` column).
- Cross-user mutations (status changes, updates, deletions) are rejected at both the service interface (`Db.Forbidden`) and HTTP layer (`403 Forbidden`).
- The live UI visually demonstrates this security perimeter: switching identities between `alice` and `bob` highlights unauthorized action barriers with immediate diagnostic feedback.

### 2. ACID Transactional Ownership Transfer with Rollback Hook
- Ownership transfer executes in an explicit transactional block with pessimistic row locking:
  - **PostgreSQL**: `BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED; SELECT ... FOR UPDATE;`
  - **SQL Server**: `SET TRANSACTION ISOLATION LEVEL READ COMMITTED; SELECT ... WITH (UPDLOCK, ROWLOCK);`
- Includes a dedicated test seam (`Runnable afterUpdate`) that injects forced exceptions post-update to prove that connection failures or runtime crashes automatically trigger `ROLLBACK`, leaving original ownership completely untouched.

### 3. Checksummed & Idempotent Schema Migrations
- Lightweight custom migration runner strictly orders `V1__init.sql` and `V2__status.sql`.
- Records SHA-256 hashes in `schema_migrations`.
- Handles T-SQL comment parsing: strips full-line `--` comments before semicolon statement splitting to avoid SQL Server batch syntax errors.

---

## Live Verification & Test Contracts

The backend test contract executes **9 JUnit 5 test cases identically** against both live local PostgreSQL 16 and a containerized Microsoft SQL Server 2022 instance:

| Test Case | Method | Contract Verified |
| :--- | :--- | :--- |
| **01** | `DbTest.testMigrationOrderAndIdempotence` | Sequential execution, checksum ledger validation, idempotent startup. |
| **02** | `DbTest.testOwnership403` | Rejection of unauthorized mutations with `Db.Forbidden`. |
| **03** | `DbTest.testSearchAndPaginationLimits` | Search matching and strict 50-item page size cap. |
| **04** | `DbTest.testTransferCommit` | Successful atomic transfer commit across user accounts. |
| **05** | `DbTest.testTransferRollbackOnHook` | Atomicity proof: injected exception triggers clean `ROLLBACK`. |
| **06** | `DbTest.testValidation` | Validation rejecting empty/whitespace titles with `Db.BadRequest`. |
| **07** | `ApiTest.testCrudRoundTrip` | Full REST lifecycle (POST 201, GET 200, PATCH 200, DELETE 200). |
| **08** | `ApiTest.testOwnershipHttp403` | Verification that `Db.Forbidden` maps cleanly to HTTP 403. |
| **09** | `ApiTest.testPaginationAndResponseCodes` | 404 on missing records, 405 on illegal methods, pagination envelope. |

**Evidence Hash**: `fdc15ce8592265882b31eb3c495c5d642b847c4ad6acffe035abbf9d3781690d` (Recorded in `results/verification.json`).

---

## Local Development & Reproduction

### Prerequisites
- Java 17+ (JDK) & Maven
- Node.js 18+ (for frontend)
- Local PostgreSQL 16 or Docker for SQL Server 2022

### Commands
```bash
# 1. Run local PostgreSQL cluster & backend tests
./pg.sh

# 2. Run backend JUnit tests against SQL Server 2022 (Docker)
cd backend
mvn test -DjdbcUrl="jdbc:sqlserver://127.0.0.1:14333;databaseName=readingqueue;user=sa;password=YourPassword123;encrypt=false" -Dmigrations="../db/sqlserver"

# 3. Run frontend development server
cd ../ui
npm install
npm run dev

# 4. Run frontend unit tests (rules & SQL generators)
node --experimental-strip-types --test "tests/*.test.ts"
```
