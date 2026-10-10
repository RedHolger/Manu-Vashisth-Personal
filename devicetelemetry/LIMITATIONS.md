# DeviceTelemetry — LIMITATIONS

- Synthetic protocol invented for this lab; not ResMed hardware, not any real
  medical-device bus. No device, clinical, safety, or regulatory claims.
- Fault injection is scripted corruption of a synthetic stream, not
  hardware-in-the-loop testing.
- CRC16/sequence/range checks cover the documented 12-byte format only.
- Local-machine results (macOS arm64, Apple clang sanitizers), not
  cross-platform guarantees.
- Does not satisfy a medical-device, firmware, or on-call qualification
  requirement; supports role 09 only as documented simulation work.
