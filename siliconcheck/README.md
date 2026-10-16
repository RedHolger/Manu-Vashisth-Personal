# SiliconCheck

A parameterized synchronous FIFO and an AXI-Stream adapter, tested with cocotb and Icarus Verilog. The scoreboards check that words arrive in order under reset, backpressure, wraparound and full/empty boundary conditions.

The regression covers depths 4, 16 and 64, using both the FIFO and stream adapter. This is RTL simulation; synthesis, timing closure and board testing are separate work.

## Run a simulation

Install Icarus Verilog, Make, Python 3 and cocotb. With that environment active, run from `sim/`:

```bash
make TOP=fifo TESTMOD=test_fifo DEPTH=16 DW=32
make TOP=axis_adapter TESTMOD=test_axis DEPTH=16 DW=32
```

`run_all.sh` runs the six saved configurations and writes `results/regression.json`. It includes the author's Python environment path for generating the summary; update `VENV` before using that wrapper elsewhere.

`rtl/fifo.sv` contains the occupancy and conservation logic; `rtl/axis_adapter.sv` maps FIFO state to ready/valid signaling. Tests are in `tests/test_fifo.py` and `tests/test_axis.py`. See [EVIDENCE.md](EVIDENCE.md) for saved simulator output.
