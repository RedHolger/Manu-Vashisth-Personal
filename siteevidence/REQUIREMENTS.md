# SiteEvidence — requirements map

| Requirement (BUILD_PROMPTS construction) | Check | Result |
|---|---|---|
| FastAPI/React/SQLite tracker | api.py + ui/ build green | pass |
| Revisions/owners/due dates/evidence/weekly | seeded + endpoints | pass |
| Missing-evidence test | INSP-1 flagged | pass |
| Overdue test | RFI-1 flagged | pass |
| Revision-mismatch test | INSP-1 rev 1 vs 2 | pass |
| Audit test | mutations append audit rows | pass |
| Handover pack | handover.json + handover.html | pass |
| No civil/surveying/site claims | LIMITATIONS.md + pack note | stated |
