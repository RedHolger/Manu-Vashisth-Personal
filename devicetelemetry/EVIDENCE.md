# DeviceTelemetry — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, Apple clang (g++), `-std=c++17 -O1 -g
-fsanitize=address,undefined -fno-omit-frame-pointer`, system Python 3.14.7
stdlib only. Seed 7 (sim takes `<scenario> <seed>`; xorshift32, reproducible).

## Commands (exit 0)

- `make test` → sim builds clean; 8/8 harness tests OK (CRC vector, clean,
  corrupt×2, drop, reorder, range, reset-ack, malformed).
- `for sc in clean corrupt drop reorder range; do ./build/sim $sc 7; done` →
  all exit 0 with zero sanitizer diagnostics; `nm` shows 48 asan/ubsan symbols
  linked (`___asan_init`, `__ubsan_handle_*`).
- `make demo` → `results/demo_clean.json` (STREAMING, no events),
  `results/demo_corrupt.json` (FAULT; CORRUPT_FRAME lines 6, 18; SEQ_GAP 16→18).

## Claim basis for CV 09 (role 09 only)

- "Built a C++ synthetic sensor-frame simulator (CRC16, seeded
  corrupt/drop/reorder/out-of-range injection) with a Python read-only monitor
  enforcing checksum, sequence, range and fault/reset state handling."
- "8-test suite passes; AddressSanitizer/UBSan runs clean; documented as
  simulation-only with no device or clinical claims."
