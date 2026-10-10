# SiteEvidence Demo — SPEC (Milestone 1)

Scope: synthetic RFI/inspection tracker for role 38 (Flynn construction
placement — NOT a software role; transferable documentation/coordination only).
FastAPI + sqlite + React/TS. Frozen TODAY = 2026-10-08. No site, no surveying,
no civil competence — stated everywhere.

## Domain (seeded, deterministic)

- RFIs: id, title, owner, due_date, status (open/answered/closed), rev_current.
- Revisions: (rfi_id, rev, note, superseded_by NULL-able).
- Inspections: id, rfi_id, rev_tested, date, result (pass/fail), evidence
  (nullable link label).
- Audit: append-only (actor, action, detail, timestamp).

## Rules (pure Python, unit-tested with hand calcs)

- Overdue: status open AND due_date < TODAY.
- Missing evidence: result pass AND evidence NULL.
- Revision mismatch: inspection.rev_tested != RFI rev_current.
- Mutations (add RFI/inspection/revision/close) append audit rows.

## Seed (asserted)

- RFI-1 parapet flashing (AO, due 09-20, rev 2, open) → OVERDUE.
- RFI-2 expansion joint (BK, due 10-15, rev 1, open) → not overdue.
- RFI-3 sealant spec (CM, due 09-25, rev 1, answered) → not overdue.
- INSP-1 on RFI-1 rev 1, pass, evidence NULL → mismatch AND missing evidence.
- INSP-2 on RFI-2 rev 1, pass, "photo-221" → clean.
- INSP-3 on RFI-3 rev 1, fail, "photo-222" → failed list.
Expected: overdue [RFI-1]; missing [INSP-1]; mismatch [(INSP-1, tested 1,
current 2)]; handover contains all RFIs/inspections + the gap lists.

## API + UI + acceptance

FastAPI: GET /rfis, /inspections, /report/weekly, /handover; POST mutations
with audit. React: RFI list with overdue badges, revision history, weekly view.
TS tests for overdue/bucket label helpers. Handover = JSON + static HTML pack.
