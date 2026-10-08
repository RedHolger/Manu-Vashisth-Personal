# Engineering Portfolio — Manu Vashisth

Applied-systems portfolio: durable execution, reliable data movement,
permission-aware retrieval, experimentation, and hardware-adjacent validation.
Every project runs locally, keeps its tests green, and states its limits
plainly — including what still needs hardware, participants, or review.

## Projects

| Directory | What it is |
|---|---|
| `flow-ledger/` | Durable job execution (Java/Spring/Postgres): idempotent submission, outbox relay, lease fencing, crash-tested. |
| `evidence-rag/` | Tenant-isolated retrieval with cited-or-abstain answers (Python/FastAPI/pgvector). |
| `data-bridge/` | Resumable paginated imports into Postgres, proven across SIGKILL faults. |
| `experiment-lab/` | Randomized experiment analysis: contracts, A/A validation, covariate adjustment. |
| `cohort-lens/` | Cohort retention with Python/SQL agreement and a traceable dashboard. |
| `shift-bench/` | Robustness benchmarking under predeclared corruptions, with ablations. |
| `cura-loop/` | Active-learning loop on hidden labels: versioned annotations, fair comparison. |
| `access-guard/` | Authorization test harness: independent policy oracle vs a lab HTTP app. |
| `incident-replay/` | Reproducible incident workbench: ingestion, detection scoring, remediation replay. |
| `ops-console/` | Accessible incident-evidence viewer (static HTML/JS, XSS-safe by construction). |
| `study-path/` | Prerequisite-aware study planner with safe import/export. |
| `user-evidence/` | Usability research instruments: protocol, consent-gated capture, analysis. |
| `release-plan/` | Release management against real repo history: charter, readiness, gates. |
| `launch-lab/` | Discovery-to-decision tooling: evidence-linked ranking, pilot, memo. |
| `fleet-doctor/` | Host diagnostics with honest UNKNOWNs + a confined fault lab. |
| `packet-lab/` | Offline network-troubleshooting lab: fixtures, parser, runbook. |
| `edge-bench/` | Host CPU vision baseline + one bit-identical optimization. |
| `silicon-check/` | FIFO RTL verified against a Python model in Icarus Verilog. |
| `enclosure-lab/` | Parametric enclosure CAD (OpenSCAD + drawings) on assumed dimensions. |

SRE work (BudgetGuard/FaultLab/RecoverOps audits) lives in a separate
private repository and is not published here.

## Running things

Each folder's README lists exact commands. Python projects are stdlib-only
unless the README says otherwise (`shift-bench` needs `numpy`; see its
`requirements.txt`). JavaScript projects need only `node`. Java/Postgres
projects need Docker (`docker compose up`) — stated per project, never
assumed. `silicon-check` needs Icarus Verilog (`iverilog`) on PATH.

## Honesty notes (read before citing numbers)

- Reported metrics come from the author's own fixtures and single-machine
  runs; they are not production, population, or hardware claims.
- Several projects have explicit open gates (real hardware, consenting
  participants, licensed data, human review). Each README names what is
  verified, what is pending, and what must not be claimed.
- Nothing here is presented as reviewed, accepted, certified, or secure.
