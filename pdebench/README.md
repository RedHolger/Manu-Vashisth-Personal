# PDEBench — finite-difference baselines (1D heat, 2D Poisson)

Educational solver lab supporting role 36. Pure Python + numpy; deterministic;
no trained models, no production-CFD claims.

## Setup

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m unittest discover -s tests -v
python measure.py
```

## Layout

- `SPEC.md` — problems, thresholds, hand-calculated fixtures, scope limits.
- `src/heat1d.py` — FTCS explicit 1D heat vs closed-form sine solution; CFL violation raises.
- `src/poisson2d.py` — Jacobi 2D Poisson vs manufactured sine solution; residual stop.
- `tests/test_solvers.py` — 9 tests: fixtures, 2nd-order convergence, boundaries, negatives.
- `measure.py` → `results/measurements.json` — convergence tables, residuals, wall time, peak memory.
- `EVIDENCE.md` — commands, exit codes, environment, measured outputs.
- `LIMITATIONS.md` — skipped checks and claim boundaries.
