# Workload + device contract — P20-01 (HOST CPU, no board)

**Device: HOST CPU only. No edge board was purchased, assumed, or accessed.**
No lab access assumed. The "device under test" is this laptop CPU, reported
honestly as host — never as an edge board. Board/instrument validation is
BLOCKED (see P20-04).

## Workload (pinned)

- Kernel: Sobel-style edge magnitude (`abs(gx)+abs(gy)`, 3×3) on synthetic
  `uint8` frames. Two implementations with identical integer arithmetic:
  `project.edges` (baseline) and `workload.edges_opt` (row-hoisted).
- Frames: deterministic PRNG (`seed`), sizes {32, 64, 128}, counts per run.
  Malformed frames (ragged, <3×3, non-list) are rejected (`ValueError`) and
  counted as dropped — never crash a run.
- Warmup: 1 untimed frame before every timed run (same kernel, same size).
- Metrics: per-frame ms (list, not just mean), min/p50/p95/max/std,
  output checksum (exact-equality gate for optimizations), peak traced Python
  bytes, overrun flags, dropped count, restart determinism (same seed →
  same checksum).

## Host identity (recorded per run in the manifest)

- `platform.platform()` + `platform.processor()` + `sys.version` + CPU count.
  The manifest labels `device: 'host-cpu'`, `board_tested: false`,
  `power_watts: null`, `temperature_c: null`. Estimates are never stored in
  measured fields.

## What is NOT claimed

No board, camera, ML model, watchdog hardware, power or thermal validation.
Host timings are host timings (tracing overhead included where noted), not
edge performance and not capacity claims.
