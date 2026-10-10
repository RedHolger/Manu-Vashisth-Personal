# CommerceFunnel — requirements map

| Requirement (BUILD_PROMPTS commerce) | Check | Result |
|---|---|---|
| Synthetic views/baskets/purchases/subs/slots | 26-row frozen fixture | pass |
| Cohort analysis | weekly purchase-rate cohorts 4/5, 1/2 | pass |
| Proposed experiment | experiment.md (design only, NOT run) | documented |
| Correct dedup/denominators | UNIQUE constraint; replay test; user-level sets | pass |
| Tested fixture counts | 5 tests assert hand calcs | pass |
| Primary/guardrail + uncertainty | view_purchase + sub/ontime; Wilson CIs | pass |
| No invented conversion uplift | LIMITATIONS.md + report text | stated |
