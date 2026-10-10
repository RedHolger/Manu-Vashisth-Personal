# PartnerOps — requirements map

| Requirement (BUILD_PROMPTS partner-analytics) | Check | Result |
|---|---|---|
| Python/PostgreSQL dashboard | kpi.py + psycopg vs local PG16; report.html | pass |
| KPIs + denominators | win 5/7, avg 3-deal basis, enablement 3/5 | pass |
| Missing-data rules | NULL amount/stage handling + counts | pass |
| Data dictionary | report.html section + SPEC | pass |
| Auditable narrative, deterministic fallback | template narrative; reruns identical | pass |
| Hand-calculated SQL fixtures | 6 tests assert hand calcs | pass |
| Duplicate/null/outlier tests | dup 1, missing 2, outlier 1 excluded | pass |
| Reconciled executive report | every excluded row counted; narrative asserts | pass |
| No SAP deployment claim | LIMITATIONS.md | stated |
