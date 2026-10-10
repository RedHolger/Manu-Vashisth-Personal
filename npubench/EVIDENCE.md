# InferenceParity — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64 (CPU only), .venv-builds torch CPU 2.14.1 +
torchaudio CPU 2.11.0 + onnx 1.22.0 + onnxscript + onnxruntime 1.30.0.
KWS repo untouched (only `best.pt` read; its venv never used for the build).

## Commands (exit 0)

- `python export_package.py` → genuine sine-mel T=101 confirmed; ONNX opset
  requested 17, exporter kept 18 (recorded in meta.json); 9 inputs + torch refs.
- `python bench.py` → `results/bench.json` (reproduced; latency p50 ~0.17 ms,
  p90 ~0.22 ms, p99 ~0.4–1.1 ms across runs on shared machine).
- `python -m unittest discover -s tests -v` → 6/6 OK.

## Measured behavior

- Parity: random mel tensors ~1e-7 abs; sine-mel (saturating, |logits|~5758)
  1.46e-3 abs = rel 2.5e-7; top-1 agreement 9/9.
- Operator support: session builds on CPUExecutionProvider (all graph ops).
- Model sha256 `313f1dfd…5b0f561de`; weights `1d1c0e93…93b372`.

## Claim basis for CV 23 (role 23 only)

- "Extended the keyword-spotting model in an isolated copy with an ONNX CPU
  baseline on shared genuine-mel + seeded inputs: top-1 agreement 9/9,
  relative diff ~1e-7, latency percentiles recorded."
- "NPU execution skipped (no hardware); CPU numbers never presented as NPU results."
