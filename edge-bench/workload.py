"""Workload kernels and contract for EdgeBench (P20-01/03).

`edges_opt` is the ONE measured optimization (row hoisting + local binding)
over the reference `project.edges`. Same integer arithmetic, so outputs must
be bit-identical — `verify_equivalence()` enforces it and P20-03 gates on it.
Frames are deterministic; malformed frames raise (callers count them dropped).
"""
import random

import project


def make_frames(n=12, size=64, seed=7):
    if n < 1 or size < 3:
        raise ValueError('invalid benchmark dimensions')
    rng = random.Random(seed)
    return [[[rng.randrange(256) for _ in range(size)] for _ in range(size)]
            for _ in range(n)]


def edges_opt(frame):
    """Row-hoisted Sobel magnitude. Contract identical to `project.edges`."""
    if (not isinstance(frame, list) or len(frame) < 3
            or not all(isinstance(r, list) and len(r) == len(frame[0])
                       and len(r) >= 3 for r in frame)):
        raise ValueError('rectangular frame >=3x3')
    out = []
    for y in range(1, len(frame) - 1):
        r0, r1, r2 = frame[y - 1], frame[y], frame[y + 1]
        row = []
        for x in range(1, len(r0) - 1):
            a0, a2 = r0[x - 1], r0[x + 1]
            b0, b2 = r1[x - 1], r1[x + 1]
            c0, c1, c2 = r2[x - 1], r2[x], r2[x + 1]
            gx = a2 + 2 * b2 + c2 - a0 - 2 * b0 - c0
            gy = c0 + 2 * c1 + c2 - a0 - 2 * r0[x] - a2
            row.append(abs(gx) + abs(gy))
        out.append(row)
    return out


def verify_equivalence(seeds=(7, 8), sizes=(32, 64)):
    """Bit-identical outputs of baseline vs optimized across fixtures."""
    for seed in seeds:
        for size in sizes:
            for frame in make_frames(3, size, seed):
                if project.edges(frame) != edges_opt(frame):
                    return False
    return True


def workload_contract():
    return {'workload': 'sobel-magnitude-3x3-synthetic-uint8',
            'kernels': ['project.edges (baseline)',
                        'workload.edges_opt (row-hoisted)'],
            'frame_sizes': [32, 64, 128],
            'warmup': '1 untimed frame, same kernel+size',
            'device': 'host-cpu (NO board; board_tested=false)',
            'metrics': ['per-frame ms list', 'min/p50/p95/max/std',
                        'output checksum (exact)', 'peak traced bytes',
                        'overruns', 'dropped', 'restart checksum']}
