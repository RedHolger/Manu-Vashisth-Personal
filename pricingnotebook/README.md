# PricingNotebook

A frequency/severity modelling exercise where the generating parameters are known. The dataset is synthetic, which makes it possible to check whether fitting recovers the intended effects before interpreting the predictions.

The implementation uses Poisson IRLS with exposure offsets for claim frequency and least squares on log severity. Evaluation includes calibration, an out-of-time split and bootstrap uncertainty.

## Fit and evaluate

Use Python 3 with NumPy installed. From this directory:

```bash
python3 -m unittest discover -s tests -v
python3 fit.py
```

The report is saved to `results/fit.json`. `datasets/policies.csv` and `datasets/truth.json` hold the frozen inputs and generating parameters. `src/generate.py` can recreate them, but is not needed for a normal run.

Read [INTERPRETATION.md](INTERPRETATION.md) for the effects and assumptions, and [SPEC.md](SPEC.md) for the experiment design. This is a statistical modelling exercise, not a pricing model approved for operational use.
