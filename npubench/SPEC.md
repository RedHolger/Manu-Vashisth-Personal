# InferenceParity Bench — SPEC (Milestone 1)

Scope: isolated ONNX-CPU parity baseline for the KWS TC-ResNet, for role 23
(Intel NPU internship). Proves the export/measure workflow; does NOT claim any
NPU execution.

## Inputs (all inside `projects/builds/npubench/`; original repo untouched)

- `vendor/tc_resnet.py` — copy of the KWS model definition (see PROVENANCE.md).
- Weights: `best.pt` state_dict (316,154 params) read from the KWS repo at export
  time; sha recorded, never modified.
- Test inputs: (a) genuine mel-spectrogram of a synthetic 1 kHz sine (torchaudio,
  exact dataset.yaml params: 16 kHz, n_fft 512, hop 160, win 400, n_mels 40 →
  T=101 frames); (b) seeded (seed 7) random batch of 8 mel tensors. Same tensors
  feed torch and ORT — "same preprocessing/model inputs".

## Procedure

1. Export (.venv-builds, torch CPU 2.14.1): model.eval, torch.onnx.export
   (opset requested 17, exporter kept 18 after failed downgrade — recorded
   honestly in meta.json), input (1,1,40,101); save `package/model.onnx` +
   torch reference logits + `meta.json` (hashes, versions).
2. Bench (.venv-builds, onnxruntime 1.30 CPU EP): parity (max|diff|, mean|diff|,
   top-1 agreement over the 9 inputs), operator support (session builds = all
   ops supported by CPU EP), latency (20 warmup + 200 timed, p50/p90/p99),
   record versions/hardware/model sha256 → `results/bench.json`.

## Acceptance thresholds

- max|logit diff| < 1e-4, top-1 agreement 9/9, session builds on CPU EP.
- Latency percentiles reported, not claimed as NPU projections.

## Explicitly out of scope (SKIPPED, not successful)

- OpenVINO backend (optional per prompt; not installed — Intel-only relevance,
  CPU-equivalent here).
- Actual NPU execution (no NPU hardware on this machine). CPU numbers are NEVER
  relabeled. CoreML EP present on this Mac but untested (see LIMITATIONS.md).
