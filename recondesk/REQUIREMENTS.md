# ReconciliationDesk — requirements map

| Requirement (BUILD_PROMPTS treasury) | Check | Result |
|---|---|---|
| Simulated invoice-payment reconciliation | sqlite ledger, ref matching | pass |
| Currencies + settlement dates | USD/GBP→EUR half-up; value/due dates | pass |
| Exceptions | duplicate, unmatched, overpayment paths | pass |
| Working-capital dashboard | report.json + static report.html | pass |
| Business definitions documented | SPEC.md + report header | pass |
| Balanced hand-calculated fixtures | 6 tests incl. tie-out (invoiced = open + allocated) | pass |
| Duplicates/partial/FX-rounding | dedicated cases (incl. half-up 0.92→1, dust tolerance) | pass |
| Exception aging + executive report | buckets asserted; match rate with denominator | pass |
| No regulated advice / bank claims | LIMITATIONS.md + report footer | stated |
