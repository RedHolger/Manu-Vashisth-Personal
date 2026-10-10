# PrivacyEval — requirements map

| Requirement (BUILD_PROMPTS privacy) | Check | Result |
|---|---|---|
| Isolated RAG copy + canary secrets | store seeds 2 synthetic canaries; fixtures labeled | done |
| Frozen attack/benign datasets | 12 attacks + 8 benign, committed JSON | done |
| Baseline vs controls comparison | leakage 5/12 vs 0/12; success 10/12 vs 0/12 | pass |
| Leakage + attack denominators | "x/12" asserted in tests | pass |
| Benign utility | 7/8 vs 8/8 (controls ≥ baseline−1) | pass |
| Uncertainty | Wilson 95% CI on both rates | pass |
| Stale-cache test | v1 visible baseline only; controls serve v2 ("30 days") | pass |
| Revocation test | bob→beta revoked: controls abstain, baseline answers | pass |
| No private data; auth ≠ DP | LIMITATIONS.md | stated |
