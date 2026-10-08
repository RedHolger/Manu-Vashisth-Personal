# EdgeBench — host CPU vision baseline, honestly labeled

A pinned Sobel workload (synthetic frames, fixed seeds/sizes, one warmup
frame) measured per-frame with variability, dropped-input handling, watchdog
flags and restart determinism — on the host CPU, labeled as such. Includes
one bit-identical optimization (row hoisting) with latency/memory tradeoffs
stated. Power and thermal instruments don't exist here, so those fields stay
null and their accessors raise instead of returning estimates. Pure Python,
stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 15 tests
```

Recorded (host, traced): baseline p50 13.95 / p95 14.37 ms per 64×64 frame;
optimized 0.96× traced with identical checksums. Tracing overhead disclosed;
untraced context ~1.5 ms. Host timings are not edge performance.

## Limits

No board, camera, model, watchdog hardware, power or thermal validation.
One CPython micro-optimization; estimates never fill measured fields by
construction.
