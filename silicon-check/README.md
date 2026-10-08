# SiliconCheck — FIFO RTL verified against a Python model, for real

A bounded FIFO in SystemVerilog, verified in Icarus Verilog against an
independent Python reference: directed tests with waveforms, 1032
differential cycles (seeded + wraparound/simultaneous/reset-mid-traces) with
zero mismatches, structural + scoreboard assertions, and a seeded
simultaneous-count defect caught twice (90 differential mismatches and an
assertion fatal, failing seed preserved). Simulation, synthesis and board
evidence are recorded as separate statuses — only simulation is claimed.

## Run it (needs Icarus Verilog on PATH)

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 24 tests
```

## Limits

DEPTH=4/WIDTH=8 only; no clock-domain crossing, X-reset, timing, formal,
synthesis (no toolchain here) or board evidence. Simulation success is not
silicon sign-off and is never called that.
