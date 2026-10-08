# ShiftBench — robustness benchmarking with honest negatives

Does a noise-augmented centroid survive distribution shift better than a
plain one? Predeclared corruptions and severities, frozen entity splits,
validation-only calibration, three seeds — and the augmented variant
*loses* on this fixture, reported as-is with ablations. Python + numpy.

## Run it

```sh
pip install -r requirements.txt
python3 -B -m unittest discover -p 'test_*.py'   # 21 tests
```

Recorded: CC0 entity set, hashed 18/6/6 splits, byte-identical checkpoint
reloads; accuracy/NLL/ECE/risk–coverage per group and seed. The headline is
a negative result (augmentation 0.944 vs baseline 0.967 on gaussian-noise,
means) — kept un-tuned.

## Limits

Synthetic stand-in data, nonclinical, no device or clinical-utility claims.
Small fixture; rankings are not general robustness claims.
