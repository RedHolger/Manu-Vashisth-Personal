# Release charter — R1-trio1-review

Machine-readable source of truth: **`charter.json`** (validated by
`releaseplan.py`, measured by `measure_p16_01.py`). This file is the readable
view; if the two disagree, `charter.json` wins.

- **Release:** Trio 1 review-bundle release — P04 FlowLedger, P06 DataBridge,
  P05 EvidenceRAG, later extended by recorded change to P07–P10.
- **Repository:** `/Volumes/MANU_DISK/google/Google_2027` (single local git
  repo, no remote).
- **Owner:** RedHolger `<manuvashisth963@gmail.com>` — the real git author of
  every commit in scope.
- **Team size:** **1. This is a SOLO release.** No cross-functional team,
  reviewer, QA, PM or SRE took part. AI coding agents (`Co-Authored-By:
  opencode`) acted as tools of the owner and are **not** collaborators.
- **Charter authored:** 2026-10-08, retrospectively, from the real repository
  state. It reconstructs the release that actually happened; it does not
  predict one.

## Why JSON and not YAML

`SPEC.md` lists "YAML/JSON". Python 3 stdlib has no YAML parser and this
project installs nothing, so the charter is JSON. Recorded as decision
`DECISIONS.md` (kit) #5.

---

## 1. Approved baseline — `R1-BASELINE-2026-10-05` (FROZEN)

Approved **2026-10-05** by the portfolio owner, recorded in `PLAN.md` § *User
decisions and approvals*, committed in `29908c6`:

> 2026-10-05: the user authorized completing the whole triplet (P04, P06, P05)
> in one continuous batch and then receiving a review ZIP for each of the three
> projects.

Planning document of record: `TRIO1_P04-P06_PLAN.md` (committed `b1e974f`,
2026-10-03, status *"plan review only. No implementation."*). Its §7 stop rule
— *"after each project's v1 evidence package, pause for user assessment"* — was
part of the approved baseline and is modelled as the two zero-hour tasks
`stop-p04` and `stop-p06`.

**Baseline scope:** flow-ledger, data-bridge, evidence-rag; four
acceptance cards each; one implementation-inclusive review ZIP each.

**Explicitly out of scope at baseline:** P07–P22 (*"Not authorized and still
withheld: … starting P07–P22"* — `PLAN.md`), CV work, marking anything
ACCEPTED, creating or moving tags beyond `p04-v1` / `p04-v1-complete`, pushing
to a remote, production deployment.

**Baseline effort estimate:** 135–210 focused hours (P04 45–70, P06 35–55,
P05 55–85) = *"≈12–27 weeks"* at a self-chosen 8–12 h/week, per
`TRIO1_P04-P06_PLAN.md` §1. Per-card hours are an **even quarter of each
project's documented range midpoint** and are labelled as estimates in every
task's `hours_basis`. **No timesheet exists; hours are planning numbers, never
measured effort.**

### Baseline milestones

| id | milestone | planned | actual commit | actual (UTC) | status |
|---|---|---|---|---|---|
| M0 | Trio 1 baseline approved | 2026-10-05 | `29908c6` | 2026-10-05T06:28:05Z | ACHIEVED |
| M1 | P04-01..04 delivered | 2026-10-05 | `9c2903d` | 2026-10-05T08:45:24Z | ACHIEVED |
| M2 | P06-01..04 delivered | 2026-10-06 | `a60d5eb` | 2026-10-06T02:43:46Z | ACHIEVED |
| M3 | P05-01..04 delivered | 2026-10-06 | `f4996a8` | 2026-10-06T21:34:32Z | ACHIEVED |
| M4 | Three review ZIPs committed | 2026-10-06 | `5f5e077` | 2026-10-06T22:07:44Z | ACHIEVED |
| M5 | User acceptance decision | after M4 | — | — | **NOT_ACHIEVED** |

Every `ACHIEVED` milestone names a commit that `measure_p16_01.py` re-checks
with `git cat-file -e`. M5 has no commit because no acceptance decision exists:
`PORTFOLIO_STATUS.md` records P04 as `CHANGES_REQUESTED` and P05/P06 as
`NOT_EVALUATED`.

### Baseline acceptance gates

| gate | what must hold | human decision? |
|---|---|---|
| `G-P04-CARDS` | P04-01..04 evidence exists; recorded exits 0 (`mvn_exit=0`, `exit=0`) | no |
| `G-P06-CARDS` | P06-01..04 evidence exists; recorded measure exits 0 | no |
| `G-P05-CARDS` | P05-01..04 evidence exists; recorded measure exits 0 | no |
| `G-BUNDLES-BUILT` | the three `opencode-handoff/bundles/*.zip` exist | no |
| `G-USER-REVIEW-TRIO1` | the user assesses the three ZIPs | **yes — has no artifact and cannot be closed by automation** |

### Baseline dependency chain and critical path

`p04-01 → p04-02 → p04-03 → p04-04 → stop-p04 → p06-01 → … → p06-04 →
stop-p06 → p05-01 → … → p05-04 → bundle-p05 → gate-user-review-trio1`
(bundles hang off each project's last card).

Computed by the unmodified reference `project.plan()`:

- **critical path (15 tasks):** the chain above ending at `bundle-p05`
- **estimated hours: 173.0** — inside the documented 135–210 range
- **ready_all: `false`** — `stop-p04` and `stop-p06` produced no artifact, and
  the reference propagates non-readiness downstream, so 13 of 18 baseline tasks
  are not ready. **The baseline plan as written could never reach ready.** It
  had to be changed; that change is CHG-001.

---

## 2. Change log — everything after the approved baseline

The baseline block in `charter.json` is `frozen: true`. `releaseplan.apply_changes`
returns a **new** effective plan and is tested never to mutate it. Every change
carries `date`, `type`, `reason`, `source` and `baseline_modified: false`.

| id | date | type | change | effect |
|---|---|---|---|---|
| **CHG-001** | 2026-10-05 | `sequencing_cut` | Batch authorization removes the two per-project stop gates (`TRIO1_P04-P06_PLAN.md` §7), for implementation work only. Source: `PLAN.md` / `29908c6`. | `stop-p04`, `stop-p06` deleted; `p06-01`→`p04-04`, `p05-01`→`p06-04`. Effort delta 0 h (removes latency, not effort). |
| **CHG-002** | 2026-10-06 | `scope_add` | Scope extended from the trio to P04–P22: *"the user requested finishing all projects before CV work."* Adds the P07–P10 analytics/ML quartet (16 cards + 1 review gate) behind the trio bundles. Source: `PLAN.md` §Scope — **uncommitted at authoring time; see P16-04 finding PF-1.** | +202.5 documented h (P07 40–65, P08 25–40, P09 50–80, P10 40–65); +4 gates. |
| **CHG-003** | 2026-10-06 | `unplanned_corrective_work` | Nine ExFAT AppleDouble `._*` sidecars were accidentally staged with the P07 kit directory and had to be removed in their own commit. Source: commit `3be4111`. | `appledouble-cleanup` (0.25 h) inserted between `p07-02` and `p07-03`, matching the real commit order `2ff5f6e → 3be4111 → 48efbaa`. |
| **CHG-004** | 2026-10-06 | `tooling_substitution` | Bundles had to be implementation-inclusive, but the kit tool `portfolio-source-kit/tools/review_bundle.py` is covered by the kit `SHA256SUMS`, so it was **not** modified; `opencode-handoff/export_impl.py` was written instead. Source: `opencode-handoff/RESUME.md` / `5f5e077`. | `bundle-export-tool` (1.0 h) in front of all three bundle tasks. |
| **CHG-005** | 2026-10-06 | `scope_cut` | CV work deferred: *"CVs are deferred."* `output/cv-pack-2026-10-06/` exists from earlier work but receives no tasks in this release. | No CV task enters the plan; the deferral is recorded instead of being silent. |
| **CHG-006** | 2026-10-08 | `process_add` | Pre-bundle preflight gate added as the P16-04 process fix, after retrospective finding PF-1 (authorization of record drifted from delivered work; root status docs stale). | `preflight-doc-freshness` (1.0 h) added in front of `gate-user-review-p07-p10`. Root-level adoption is a **recommendation only**; nothing outside `release-plan/` was modified. |

### Effective plan (baseline + CHG-001…CHG-006)

- **36 tasks** (18 baseline − 2 removed + 20 added) across P04–P10 plus
  `opencode-handoff`, `portfolio-source-kit` and `release-plan`
- **critical path (32 tasks):** P04 → P06 → P05 → `bundle-export-tool` →
  `bundle-p04` → P07 (with `appledouble-cleanup`) → P08 → P09 → P10 →
  `preflight-doc-freshness`
- **estimated hours: 377.75**, inside the summed documented range **290–460 h**
- **ready_all: `false`** — the only unmet tasks are the two human review gates
  `gate-user-review-trio1` and `gate-user-review-p07-p10`.

## 3. Release status

**DELIVERED, NOT ACCEPTED.** All 34 automated delivery tasks verify against
artifacts that exist on disk with recorded exit status 0 (see
`results/p16-02-verification/`). Both acceptance gates are human decisions with
no artifact and stay permanently unmet until the owner reviews. Nothing in this
project may mark a release ACCEPTED.

## 4. Known limitations of this charter

- Hours are planning estimates, not measured effort; no timesheet was kept.
- The charter was authored **after** delivery (2026-10-08), so "planned" dates
  come from `TRIO1_P04-P06_PLAN.md` / `PLAN.md` while "actual" dates come from
  git. Planned dates for M2–M4 are day-granular because no finer commitment was
  ever written down.
- CHG-002's authorization exists only in the uncommitted working tree. That is
  a real governance defect, reported as PF-1 in P16-04 rather than repaired
  silently (repairing it would mean editing `PLAN.md`, outside this project).
- Solo release: this charter demonstrates release *planning and evidence
  discipline*, not cross-functional leadership.
