# PricingNotebook — requirements map

| Requirement (BUILD_PROMPTS actuarial) | Check | Result |
|---|---|---|
| Synthetic frequency/severity GLMs | Poisson IRLS + log OLS, from scratch | pass |
| Exposure offsets | log(exposure) offset; positive-exposure test | pass |
| Out-of-time split + baseline | periods 1–7 vs 8–10; intercept-only baseline; lift +52.6 deviance pts | pass |
| Leakage tests | disjoint periods, clean exposures, closed-form checks | pass |
| Calibration | decile table, tracks within 0.15 | pass |
| Uncertainty | Fisher SEs + bootstrap CI on lift (entirely positive) | pass |
| Assumptions + interpretation | INTERPRETATION.md | pass |
| No exams / approved pricing | LIMITATIONS.md | stated |
