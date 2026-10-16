# ReadingQueue

A Java reading-list API with PostgreSQL and SQL Server adapters, plus a React interface for exploring ownership rules and transactions. The main question is whether the same service contract behaves consistently across both databases.

Items have owners, statuses and searchable titles. Ownership transfer uses a transaction and row locks; a test hook introduces a failure after the update to check rollback. Versioned migrations record checksums so a changed migration can be detected.

## Backend checks

Requirements: Java 17+, Maven and PostgreSQL 16 command-line tools on PATH.

```bash
bash pg.sh
```

The helper creates a project-local cluster on port 55433, runs the fixture tests and stops the cluster afterward. For SQL Server, use the instructions in [SETUP_SQLSERVER.md](SETUP_SQLSERVER.md) with a disposable test database. Tests delete fixture rows, so do not point them at a database containing work you need.

Saved results cover the same nine JUnit tests on PostgreSQL 16 and SQL Server 2022. See [EVIDENCE.md](EVIDENCE.md) for the recorded runs; the count is historical, not a live status badge.

## Frontend

With Node.js installed, run from `ui/`:

```bash
npm ci
npm run build
npm run dev
```

The frontend uses port 5175. The committed UI can fall back to in-memory demo data when its API is unavailable; browser interactions alone therefore do not prove that a database transaction ran. Its `X-User` identity header is a lab mechanism, not production authentication.

Database adapters are under `backend/src/main/java/queue/`, migrations under `db/`, and the UI under `ui/src/`. The PostgreSQL and SQL Server differences are kept in their respective adapters rather than spread through the HTTP handlers.
