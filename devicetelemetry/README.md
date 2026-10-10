# DeviceTelemetry Lab — C++ sensor-frame simulator + Python monitor

Simulation-only lab supporting role 09. No hardware, no clinical claims
(see LIMITATIONS.md).

## Setup

```
make test   # builds sim with ASan+UBSan, runs 8 harness tests
make demo   # clean + corrupt pipelines into results/
```

## Layout

- `SPEC.md` — synthetic 12-byte frame protocol, state machine, scope.
- `src/sim.cpp` — seeded emitter (clean/corrupt/drop/reorder/range), CRC16-CCITT.
- `src/harness.py` — stdlib read-only monitor: CRC/seq/range checks, FAULT latch,
  reset-ack recovery, timestamped evidence JSON.
- `tests/test_harness.py` — 8 tests incl. CRC check-vector 0x29B1.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
