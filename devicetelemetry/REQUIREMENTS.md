# DeviceTelemetry — requirements map

| Requirement (BUILD_PROMPTS device) | Test / check | Result |
|---|---|---|
| Checksum | CRC-16/CCITT-FALSE check-vector 0x29B1; corrupt scenario → 2 bad-crc | pass |
| Safe transition | clean → STREAMING; gaps don't latch FAULT | pass |
| Fault tests | corrupt → FAULT; out-of-range 9000 → FAULT + OUT_OF_RANGE | pass |
| Reset tests | reset-ack in FAULT → IDLE + RESET_OK | pass |
| Dropped/reordered | SEQ_GAP (drop) / SEQ_REGRESSION (reorder) detected | pass |
| Sanitizer run | ASan+UBSan build; 5 scenarios exit 0, 0 diagnostics; 48 san symbols linked | pass |
| Requirements doc | this file + SPEC.md | done |
| No real-device/clinical claims | LIMITATIONS.md | stated, unclaimed |
