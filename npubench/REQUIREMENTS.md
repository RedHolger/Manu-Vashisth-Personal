# InferenceParity — requirements map

| Requirement (BUILD_PROMPTS npu) | Check | Result |
|---|---|---|
| Isolated KWS extension | vendor copy + PROVENANCE; original repo untouched | done |
| ONNX CPU baseline, same inputs | 9 shared inputs (genuine sine-mel + 8 seeded) | done |
| Output parity | max abs 1.46e-3 on saturated sine-mel (rel 2.5e-7); ~1e-7 on randoms; top-1 9/9 | pass |
| Operator support | session builds on CPUExecutionProvider | pass |
| Warmup/latency percentiles | 20 + 200 iters; p50/p90/p99 recorded | pass |
| Versions/hardware/model hash | torch 2.14.1, ort 1.30.0, arm64 CPU, sha256 recorded | pass |
| NPU execution skipped, never relabeled | test_npu_marked_skipped; LIMITATIONS.md | stated |
| OpenVINO backend (optional) | not installed | SKIPPED (Intel-only relevance; CPU-equivalent here) |
