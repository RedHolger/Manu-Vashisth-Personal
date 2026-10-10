# PricingNotebook — SPEC (Milestone 1)

Scope: educational frequency/severity GLMs on synthetic data with KNOWN true
parameters, for role 35 (Allianz actuarial — requirement unmet; this is
transferable analytical work, stated as such). numpy only.

## Data (src/generate.py, seed 5, frozen datasets/policies.csv)

800 policies × 10 monthly periods = 8000 rows: {policy, period, young, urban,
suv, exposure∈[0.5,1.0]}. Truth:
- frequency: claims ~ Poisson(exposure × exp(−2.0 + 0.6·young + 0.5·urban + 0.3·suv)).
- severity: each claim amount ~ LogNormal(6.5 + 0.2·suv + 0.1·urban, 0.4);
  row stores total paid + claim count.
Out-of-time split: train periods 1–7, test 8–10 (leakage test asserts disjoint
periods and positive exposure).

## Models (src/glm.py: from-scratch IRLS, no sklearn)

- Frequency: Poisson GLM, log link, offset log(exposure). IRLS to tol 1e-8.
- Severity: OLS on log(mean severity) for rows with ≥1 claim (documented
  log-scale linear proxy, not a Gamma IRLS — stated openly).
- Baseline: intercept-only (grand mean) both parts; lift = test deviance
  (model) vs baseline.

## Acceptance mapping

- Leakage tests: period disjointness, exposure > 0, no NaN, features pre-date
  outcomes by construction (row = one policy-month, documented).
- Calibration: predicted-vs-actual frequency by decile table.
- Uncertainty: Fisher SEs from IRLS + bootstrap CI (seed 42, 500 resamples)
  on test lift.
- Assumptions + interpretation: INTERPRETATION.md (log-link multiplicative
  effects; recovery of TRUE params asserted: |β̂−β| < 0.1 frequency).
- No exams, no approved-pricing, no advice (LIMITATIONS.md).
