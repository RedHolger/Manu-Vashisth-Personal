# SiliconCheck — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, Icarus Verilog 13.0 (brew), cocotb 2.1.0,
Python 3.14, seeds fixed in tests (42/7/1234).

## Commands (exit 0)

- `cd sim && ./run_all.sh` → `results/regression.json`: 6/6 configs pass:
  fifo×{4x8, 16x32, 64x32} 5/5 tests each; axis_adapter×same 2/2 each.
  (Two pre-fix iterations failed honestly on testbench races and were rewritten;
  final run_all exit 0; per-run logs in /tmp/sim_*.log.)

## Measured behavior (not benchmarks, functional proof)

- Fill-to-full asserts `full` with `count == DEPTH` at all depths; 4 extra
  writes ignored, original order intact on drain.
- 6xDEPTH+5 mixed read/write steps: scoreboard order + occupancy every cycle.
- Stream: 4xDEPTH+3 seeded words through random both-side stalls, order exact.
- Overflow: `s_ready` deasserts at DEPTH; drain returns words 0..DEPTH-1 in order.

## Debugging note (kept as evidence of rigor)

First stream-test version used post-edge signal sampling and same-timestep
drive/edge awaits, producing a phantom pop + lost writes (caught by the
scoreboard: rx[0]=0 shift, 17/19 received). Rewrote all drivers to
falling-edge-drive / rising-edge-sample with pre-edge handshake bookkeeping;
regression green since. Fixture: none — live RTL sim throughout.

## Claim basis for CVs 27/37 (both roles)

- "Built parameterized SystemVerilog FIFO + AXI-Stream adapter; verified reset,
  wraparound, backpressure, ordering and overflow/underflow with cocotb/Icarus
  across DEPTH 4/16/64 (7 tests, seeded scoreboards, regression JSON)."
- "No synthesis/timing-closure claims; HLS demo work kept separate."
