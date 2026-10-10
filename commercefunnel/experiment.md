# Proposed experiment: slot-upgrade nudge (PROPOSAL ONLY — never run)

Status: design document. No traffic was allocated, no users were treated,
no results exist. Writing this down does not make it an experiment.

## Hypothesis

Offering a free delivery-slot upgrade at basket time raises view→purchase
conversion for the treated cohort week.

## Design

- Unit of randomization: user. Population: users with ≥1 basket event.
- Arms: control (standard slots) vs treated (free upgrade offer).
- Primary metric: view→purchase conversion, denominator = distinct viewers.
- Guardrails: substitution acceptance must not drop; slot on-time rate must
  not drop (upgrade must not overload Saturday capacity).
- Analysis: difference in proportions with Wilson CIs per arm; SRM check
  (treated share ≈ 50% of viewers); one pre-registered primary comparison.
- Minimum runtime: two full weekly cohorts (weekday effects); stop early only
  on guardrail breach with a written rule.

## Why it stays a proposal here

No live shop, no traffic, no consent framework. Running it would require the
employer's platform — this document is interview-grade design thinking only.
