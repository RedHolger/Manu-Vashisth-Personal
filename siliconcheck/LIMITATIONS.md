# SiliconCheck — LIMITATIONS

- Simulation only (Icarus Verilog, zero-delay semantics with the documented
  drive/sample discipline). No synthesis, no timing closure, no FPGA/ASIC
  device evidence — none claimed.
- Stream-words only: no TLAST/TKEEP packet framing, no clock-domain crossing.
- DEPTH must be a power of 2 (pointer wrap uses equality compare).
- Local-machine results (macOS arm64, Icarus 13.0, cocotb 2.1.0), not
  cross-simulator guarantees.
- Does not satisfy an RTL/signoff qualification requirement by itself; supports
  roles 27/37 only as documented verification work, alongside the (separate)
  PYNQ HLS demo evidence.
- HLS C++ experience is not presented as RTL experience anywhere.
