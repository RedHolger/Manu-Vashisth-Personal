# ProcessCheck Lab — batch-quality analysis (role 30)

X-bar/R charts, capability vs fictional spec limits, corrective-action log.
Teaching fixture; no GMP/regulatory validation anywhere.

## Setup (.venv-builds: numpy)

```
python -m unittest discover -s tests -v   # 6 tests
python src/generate.py                    # regenerates frozen datasets/
python report.py                           # -> results/report.{json,html}
```

## Layout

- `SPEC.md` (methods, constants, expectations).
- `src/generate.py`, `src/charts.py`, `datasets/` (batches.csv frozen, actions.json).
- `report.py`, `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
