# Simulation vs synthesis vs board evidence — P21-04 separation record

These three evidence kinds are SEPARATE. A result in one never implies a
result in another. This file records what exists, what is blocked, and what
must not be claimed.

## 1. Simulation — VERIFIED (this project)

- Icarus Verilog 13.0, `-g2012`. Directed testbench PASS, 1032-cycle
  differential with 0 mismatches, A1–A6 assertions PASS, seeded defect caught
  twice (90 differential mismatches + A6 fatal), VCD waveforms retained.
- Evidence: `results/p21-01-toolchain/`, `results/p21-02-differential/`,
  `results/p21-03-quality/`.
- Claims: the RTL `fifo.sv` (DEPTH=4/WIDTH=8) behaves per the Python model on
  the recorded traces. Nothing more.

## 2. Synthesis — BLOCKED (no toolchain)

- Probed: `yosys` binary absent; no Verilator, no commercial synthesizer.
  No netlist, no area/timing report was produced, and none is claimed.
- Smallest unblock: install an RTL synthesis toolchain, synthesize `fifo.sv`
  for a named target, and record the log + netlist + warnings as new evidence
  under `results/p21-04-separation/` (or a new card dir). Do not present
  simulation logs as synthesis evidence.

## 3. Board / FPGA — BLOCKED (no equipment)

- Probed: no FPGA toolchain (`quartus`, `vivado`, `openFPGALoader`, `nextpnr`
  all absent) and no board inventoried. No bitstream, no on-device run, no
  measured fit/thermal/power exists, and none is claimed.
- Smallest unblock: inventory real equipment, synthesize + place-and-route for
  that exact part, program it, and record device/condition/measurements as new
  evidence. Simulation waveforms are not board evidence.

## Non-conflation rule (enforced by `measure_p21_04.py`)

- No results file may claim a synthesis or board PASS. The three statuses
  (`simulation: VERIFIED`, `synthesis: BLOCKED`, `board: BLOCKED`) are stored
  as distinct fields and asserted distinct.
- Python-only or simulation-only success is never labeled RTL verification of
  synthesized silicon, and simulation is never labeled silicon sign-off.
