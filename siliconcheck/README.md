# SiliconCheck — parameterized FIFO + AXI-Stream adapter, cocotb/Icarus verified

Simulation-only lab supporting roles 27/37. No synthesis, timing closure, or
board claims (see LIMITATIONS.md).

## Setup

Needs Icarus Verilog (`brew install icarus-verilog`) and cocotb (`pip install cocotb`).

```
cd sim && ./run_all.sh        # 6 configs, writes ../results/regression.json
```

Single run: `make TOP=fifo TESTMOD=test_fifo DEPTH=16 DW=32`.

## Layout

- `SPEC.md` — DUTs, acceptance, scope limits.
- `rtl/fifo.sv` — sync FIFO, occupancy counter, conservation assertion.
- `rtl/axis_adapter.sv` — s_ready=~full, m_valid=~empty word pump.
- `tests/test_fifo.py` — 5 tests (reset/order/full/empty/wraparound+simultaneous).
- `tests/test_axis.py` — 2 tests (backpressure order, overflow blocking).
- `REQUIREMENTS.md` — acceptance map. `EVIDENCE.md`, `LIMITATIONS.md`.
