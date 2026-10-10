# Parameter interpretation (measured values in results/fit.json)

Log-link GLMs are multiplicative: a coefficient β means ×exp(β) on the mean,
all else equal. Fitted frequency effects (truth in brackets): young ×1.78
(×1.82), urban ×1.67 (×1.65), suv ×1.28 (×1.35) — recovery within standard
errors, which the IRLS Fisher information (recomputed at the final fitted
means) supplies per coefficient. Severity (log-scale OLS): intercept ≈ €665
mean claim (truth €665), suv ×1.24 (truth ×1.22); the young coefficient (+0.05)
is near zero, correctly recovering the null effect built into the generator.

Assumptions invoked (and where they break): correct link and linear predictor
(true here by construction — never assumed on real data); independent rows
(synthetic draws are independent; real policies renew and correlate);
exposure measured without error; no omitted confounders (generator has none;
reality always does). Out-of-time validation (periods 8–10) guards against
overfitting the training window but not against regime change.
