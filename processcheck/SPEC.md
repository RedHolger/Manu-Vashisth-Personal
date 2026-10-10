# ProcessCheck Lab — SPEC (Milestone 1)

Scope: synthetic batch-quality analysis for role 30 (Alcon). Unit/null checks,
X-bar/R charts, capability vs spec limits, corrective-action log. numpy only.
No GMP/medical-device regulatory validation — stated everywhere.

## Fixtures (src/generate.py, seed 3, frozen datasets/batches.csv)

Seal-width mm, subgroup n=20, 10 batches. In-control: mean 10.0, sd 0.1
(batches 1–6, 10). Out-of-control: batches 7–8 mean shifted +0.35.
Batch 9: 3 null readings + otherwise in-control. Spec limits LSL 9.55,
USL 10.45 (fictional print limits, NOT a device master record).

## Methods (src/charts.py; standard SPC constants for n=20 documented inline)

- Validation: range gate 8.0–12.0 mm (implausible values quarantined + counted);
  nulls counted per batch, excluded from statistics with counts reported.
- X-bar chart: limits from BASELINE batches 1–5 (grand mean ± A2·Rbar,
  A2=0.1796 for n=20). R chart: D3=0.4145, D4=1.5855 × Rbar. Rule 1 only
  (point beyond limits) — the only rule claimed.
- Capability (baseline data only): Cp/Cpk vs spec limits under a stated
  normality assumption (no normality test performed — openly documented).
- Actions: seeded corrective-action log; every flagged batch must have an
  action (completeness test).

## Expected (asserted)

Batches 7,8 flagged on X-bar; 1–6,10 clean; batch 9 nulls counted (3) with
clean chart verdict on valid readings; Cpk in (1.3, 1.7); report counts tie
to fixture rows.
