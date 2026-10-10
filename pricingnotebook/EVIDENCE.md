# PricingNotebook — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, .venv-builds Python 3.14.7 + numpy 2.2.6.
Deterministic (seeds 5 gen / 42 bootstrap).

## Commands (exit 0; see results/lastrun.log for the full transcript)

- `python src/generate.py` → 8000 rows, 1565 claims.
- `python fit.py` → frequency β̂ (−1.948, 0.577, 0.513, 0.244) vs truth
  (−2.0, 0.6, 0.5, 0.3); lift +77.65 deviance pts, CI (41.9, 115.3);
  severity recovers truth within 0.07; IRLS converged in 7 iterations.
- `python -m unittest discover -s tests -v` → 12/12 OK (closed forms incl.
  the varying-exposure analytical case y=[1,2,3,4]/exp=[.5,1,1.5,2] → log 2
  with predicted total exactly 10; invalid-input and non-convergence guards).

## Claim basis for CV 35 (role 35 only, partial gap)

- "Built synthetic frequency/severity GLMs from scratch (Poisson IRLS with
  exposure offsets, log-scale severity) with out-of-time validation,
  calibration, bootstrap uncertainty and known-truth parameter recovery."
- "Educational; no actuarial exams, approved pricing, or advice. Actuarial
  qualification gaps stay in the role notes."
