# EngineeringEvidence Demo — SPEC (Milestone 1)

Scope: software-only requirements/revision/review/test traceability for a
FICTIONAL cabin modification (overhead-bin latch retrofit, invented for this
lab), for role 28 (Boeing). stdlib + sqlite3; PDF via the repo's pdflatex
toolchain. Not certification, not EASA competence, stated everywhere.

## Store

requirements(id, title, rev_current, status) with a revisions table
(req_id, rev, note, live BOOL) so conflicts are representable; tests(id,
req_id, rev_tested, result pass/fail/pending, evidence TEXT NULL-able);
reviews(package signoff rows).

## Seeded defects (by design, asserted in tests)

- REQ-07 (emergency placard contrast): NO test → orphan.
- REQ-03 (latch cycle life): rev B AND rev C both live → revision conflict;
  T-03a tested rev B (pass), T-03b tests rev C (pending).
- T-05 (bin door sensor): result pass but evidence NULL → incomplete evidence.

## Outputs

`review_package.py` → traceability matrix (req × tests with rev/result),
gap list (orphans, conflicts, incomplete evidence, pending), signoff checklist
→ `results/review.json` + `results/review.tex` → compiled `results/review.pdf`.
Synthetic review package only.
