"""Host-CPU baseline runner for EdgeBench (P20-02): warmup, per-frame log.

Runs a kernel on deterministic frames with one untimed warmup frame, logs
EVERY frame's milliseconds (never just a mean), counts dropped (malformed)
frames without crashing, flags watchdog overruns, and records restart
determinism (same seed → same checksum). Device is host-cpu; power/thermal
stay null here (see `instruments.py`).
"""
import platform
import statistics
import sys
import time
import tracemalloc

import project
import workload


def stats(times):
    if not times:
        return {'n': 0}
    ordered = sorted(times)
    n = len(ordered)
    p50 = statistics.median(ordered)
    p95 = ordered[min(n - 1, int(n * 0.95))]
    mean = sum(ordered) / n
    var = sum((t - mean) ** 2 for t in ordered) / n
    return {'n': n, 'min_ms': ordered[0], 'p50_ms': p50, 'p95_ms': p95,
            'max_ms': ordered[-1], 'mean_ms': mean, 'std_ms': var ** 0.5}


def environment():
    return {'device': 'host-cpu', 'board_tested': False,
            'platform': platform.platform(),
            'processor': platform.processor() or 'unknown',
            'python': sys.version.split()[0],
            'cpu_count': __import__('os').cpu_count(),
            'power_watts': None, 'temperature_c': None}


def run(kernel='baseline', n=24, size=64, seed=7, watchdog_ms=None):
    """Timed run; `kernel` is 'baseline' or 'optimized'."""
    fn = project.edges if kernel == 'baseline' else workload.edges_opt
    frames = workload.make_frames(n, size, seed)
    fn(frames[0])  # warmup, untimed, same kernel+size
    times, checksum, dropped, overruns = [], 0, 0, []
    tracemalloc.start()
    try:
        for i, frame in enumerate(frames):
            try:
                start = time.perf_counter_ns()
                out = fn(frame)
                ms = (time.perf_counter_ns() - start) / 1e6
            except ValueError:
                dropped += 1
                continue
            times.append(ms)
            checksum += sum(map(sum, out))
            if watchdog_ms is not None and ms > watchdog_ms:
                overruns.append({'frame': i, 'ms': ms})
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return {'kernel': kernel, 'n': n, 'size': size, 'seed': seed,
            'milliseconds': times, 'stats': stats(times),
            'dropped': dropped, 'overruns': overruns,
            'output_checksum': checksum,
            'peak_traced_python_bytes': peak,
            'watchdog_ms': watchdog_ms, 'environment': environment()}


def run_with_drops(kernel='baseline', framesets=None, watchdog_ms=None):
    """Run over caller-supplied frames (may include malformed ones)."""
    fn = project.edges if kernel == 'baseline' else workload.edges_opt
    framesets = framesets if framesets is not None else []
    times, checksum, dropped = [], 0, 0
    for frame in framesets:
        try:
            start = time.perf_counter_ns()
            out = fn(frame)
            times.append((time.perf_counter_ns() - start) / 1e6)
            checksum += sum(map(sum, out))
        except ValueError:
            dropped += 1
    return {'milliseconds': times, 'stats': stats(times),
            'dropped': dropped, 'output_checksum': checksum}
