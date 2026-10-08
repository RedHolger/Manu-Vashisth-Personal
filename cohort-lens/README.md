# CohortLens — retention analysis that shows its denominators

Segmented cohort retention over explicit activation windows and cohort ages,
with Python and SQL implementations that must agree on boundary fixtures
(late events, duplicates included). A static HTML dashboard traces every
number to source tables; the decision memo stays descriptive — associations
are never called causal. Pure Python + SQL, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 28 tests
```

Recorded: Python/SQL byte-agreement on tiny fixtures; incomplete windows
excluded from complete-window denominators; `unknown` preserved (never
zero). A licensed-dataset adapter exists with manifest; real product data
is not included.

## Limits

Synthetic event streams, not real product users. Descriptive statistics
only; the dashboard is evidence-linked, not causal.
