# InferenceParity — LIMITATIONS

- CPU ONLY: no Intel NPU, no OpenVINO hardware, no Apple-Neural-Engine runs.
  CoreML EP exists on this Mac but was deliberately not used (silent CPU
  fallback would muddy the baseline). CPU latency is not an NPU projection.
- Parity inputs are one genuine-mel + eight synthetic tensors, not a speech
  eval set; no accuracy claim about the underlying KWS model (its README
  94% figure is not repeated here).
- Export opset 18 (requested 17; downgrade failed, recorded honestly).
- Local-machine results (arm64 Mac, ORT 1.30.0), not cross-platform guarantees.
- Supports role 23 only as an export/parity workflow baseline.
