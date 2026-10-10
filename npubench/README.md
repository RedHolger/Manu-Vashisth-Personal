# InferenceParity Bench — ONNX-CPU parity baseline for KWS TC-ResNet (role 23)

Isolated extension of the keyword-spotting model: export once, prove CPU parity,
measure latency. NPU execution SKIPPED (no hardware) — see LIMITATIONS.md.

## Setup (.venv-builds: torch CPU, onnx, onnxruntime)

```
python export_package.py   # torch ref + package/model.onnx (reads best.pt readonly)
python bench.py            # parity + latency -> results/bench.json
python -m unittest discover -s tests -v
```

## Layout

- `SPEC.md`, `PROVENANCE.md` (vendored model + weight hashes).
- `vendor/tc_resnet.py` — verbatim model copy (original repo untouched).
- `export_package.py`, `bench.py`, `tests/test_parity.py` (6 tests).
- `package/` (model.onnx, inputs.npz, torch_ref.npz, meta.json).
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
