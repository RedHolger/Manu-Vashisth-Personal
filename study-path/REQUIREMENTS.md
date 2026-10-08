# StudyPath requirements — P14-01 (generic curriculum, not university)

**This is a GENERIC curriculum for a study-planning exercise. It is not any
university's course requirements, and no university hub, course catalog or
enrollment data was used.** Mandatory vs optional is labeled per item below;
optional suggestions never gate progress.

## Mandatory core (prerequisite chain; all REQUIRED)

1. `pixels` — Pixels and sampling (no prerequisites).
2. `filters` — Blurring and sharpening (requires `pixels`).
3. `edges` — Edges and gradients (requires `filters`).

Completion rule (enforced): a topic completes only with completed
prerequisites; undoing a prerequisite with completed dependants is refused.
Completed prerequisites stay consistent across import/export/reload.

## Optional enrichment (SUGGESTION only; never required, never blocking)

- `color-spaces` — Color models (suggested after `pixels`; optional).
- `morphology` — Morphological ops (suggested after `filters`; optional).
- `paper-notes` — Reading notes (anytime; optional).

No optional item appears in any `requires` chain; the planner treats missing
optional topics as absent, never as blockers.

## Target-user tasks (generic; from P15 Study B)

1. Add a 90-minute study block Thursday evening. 2. Read an overlap conflict
   without losing the plan. 3. Import a plan file; invalid imports must
   preserve existing progress. Keyboard-only operation throughout.
