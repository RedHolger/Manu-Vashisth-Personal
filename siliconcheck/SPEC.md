# SiliconCheck — SPEC (Milestone 1)

Scope: parameterized SystemVerilog FIFO + AXI-Stream adapter verified with
cocotb against Icarus Verilog, for roles 27/37. Seeded scoreboard, regression JSON.

## DUTs (`rtl/`)

1. `fifo.sv` — synchronous FIFO, params DATA_WIDTH (default 32), DEPTH (default 16,
   must be power of 2). Ports: clk, rst_n, wr_en, rd_en, din, dout, full, empty,
   count. Synchronous read (data available the cycle after rd_en).
   Assertions: no write when full, no read when empty, count conservation,
   gray-style pointer wrap correctness via occupancy model.
2. `axis_adapter.sv` — wraps fifo: AXI-Stream slave in (s_valid/s_ready/s_data),
   master out (m_valid/m_ready/m_data). Backpressure: s_ready = ~full;
   m_valid = ~empty; single-cycle skid behavior documented, no packet framing
   (stream words only, TLAST/TKEEP out of scope and stated).

## Acceptance (from BUILD_PROMPTS)

Reset, wraparound, backpressure, ordering, overflow/underflow across parameters
(DEPTH 4/16/64, DATA_WIDTH 8/32); regression JSON + requirements map.
No hardware timing closure without synthesis/device evidence (stated, unclaimed).

## Out of scope

Synthesis, timing closure, board bring-up, formal proofs, TLAST/TKEEP packet mode.
