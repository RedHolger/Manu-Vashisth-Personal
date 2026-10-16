# ProcessCheck

Batch-quality analysis using X-bar/R control charts and capability estimates. The synthetic batches include seeded shifts, letting the checks compare flagged batches with known changes in the input.

The report keeps validation errors, chart signals, specification limits and corrective actions together. This makes a flagged batch traceable back to its measurements and recorded action.

## Generate the report

Use Python 3 with NumPy installed:

```bash
python3 -m unittest discover -s tests -v
python3 report.py
```

Outputs are `results/report.json` and `results/report.html`. The frozen inputs live in `datasets/`; `src/generate.py` can recreate them when intentionally changing the experiment.

`src/charts.py` contains the calculations. [SPEC.md](SPEC.md) documents the chart constants and assumptions. Specification limits are fictional, and the results have not been validated for a manufacturing or regulated process.
