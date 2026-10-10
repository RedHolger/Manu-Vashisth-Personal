# DeviceTelemetry Lab — SPEC (Milestone 1)

Scope: C++ synthetic sensor-frame/state-machine simulator + Python harness for
role 09 (ResMed Devices). Fully local: g++ with ASan/UBSan, stdlib Python.

## Protocol (synthetic, documented here — not a real device)

Frame (12 bytes, big-endian): u16 SYNC 0xA55A | u8 seq | u8 type (0x01=data,
0x02=status, 0x03=reset-ack) | i16 value (centi-units) | u16 crc16-CCITT over
first 10 bytes.

State machine: IDLE → STREAMING on host `start`; STREAMING → IDLE on `stop`;
any corrupt frame → FAULT (latch, require `reset` → RESET_SENT → IDLE on
reset-ack). Out-of-range value (|value| > 4000) → FAULT. Dropped/reordered
detection via seq gaps/regressions. Read-only view: harness never mutates sim.

## Acceptance (from BUILD_PROMPTS)

Checksum, safe transition, fault/reset tests + sanitizer run. Requirements in
REQUIREMENTS.md; no real-device or clinical claims.

## Components

- `src/sim.cpp` — simulator: emits scripted streams, applies fault injection
  (corrupt/dropped/reordered/out-of-range per seeded plan), prints frames as hex.
- `src/harness.py` — stdlib: parses frames, checks CRC, tracks seq, enforces
  state machine, emits timestamped evidence JSON.
- `tests/` — fixtures (good/corrupt/drop/reorder/range streams) + harness tests.
