# PricingNotebook — synthetic frequency/severity GLMs (role 35)

Known-truth insurance data, from-scratch IRLS, out-of-time validation.
Educational; no exams, pricing approval, or advice.

## Setup (.venv-builds: numpy)

```
python -m unittest discover -s tests -v   # 7 tests
python src/generate.py                    # regenerates frozen datasets/
python fit.py                             # -> results/fit.json
```

## Layout

- `SPEC.md` (design + truth), `INTERPRETATION.md` (effects + assumptions).
- `src/generate.py`, `src/glm.py` (Poisson IRLS + log OLS), `fit.py`.
- `datasets/` (policies.csv frozen, truth.json), `tests/test_glm.py`.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
