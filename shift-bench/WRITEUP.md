# Research note — P09 ShiftBench (synthetic stand-in, nonclinical)

- Question (predeclared): does fitting centroids on noise-augmented train
  copies improve shifted-test accuracy over plain centroids?
- Setup: P09-01 CC0 splits (18/6/6 entities), P09-02 centroid baseline,
  P09-03 corruptions; 3 seeds (0,1,2); temperature from validation only.
- Intervention: `intervention.py` — centroids fit on train + one σ1.5 noise
  copy per train image. Ablation: augmentation {off,on} x temperature
  {raw, calibrated}.

## Results (mean test accuracy, 3 seeds)

| condition | baseline | augmented |
|---|---|---|
| original | 1.000 | 1.000 |
| gaussian-noise-s1 | 0.967 | 0.944 |
| gaussian-noise-s2 | 0.828 | 0.806 |
| occlude-s1 | 1.000 | 1.000 |
| occlude-s2 | 0.500 | 0.500 |
| roll-s1 / roll-s2 | 0.500 | 0.500 |

Calibration changes NLL only, never accuracy (temperature rescales
confidence, not predictions) — identical raw/calibrated rows above.

## Reading

- The intervention **does not help**: heavy-noise accuracy drops slightly
  (0.828 → 0.806), spatial shifts stay at chance either way. This is a
  **negative result** and is reported as such.
- Known methods used as-is: nearest-centroid scoring, temperature scaling
  on validation (Guo et al. 2017 style), ECE/risk-coverage reporting. The
  **original contribution** is limited to the entity-hashed split protocol
  and the predeclared 6-corruption x 3-seed evaluation harness on this
  synthetic stand-in — not a new calibration method and not a robustness
  improvement.
- No clinical utility is claimed. The stand-in is separable bars-plus-noise;
  nothing here transfers to medical imaging or patient care. The BloodMNIST
  follow-up (see DATA_SOURCE.md) would need its own protocol rerun before
  any applied reading.

## Limitations

- One classifier family, one augmentation strength, one temperature grid.
- Three seeds; no significance testing — gaps of ~0.02 are noise.
- Synthetic data only; ablations are ablations of a toy, not evidence
  about real distribution shift.
