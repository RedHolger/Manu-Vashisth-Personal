"""Predeclared corruptions for ShiftBench (P09-03): noise, occlusion, shift.

CORRUPTIONS fixes the study before any measurement: three families x two
severities each, all deterministic in (seed, sample_index). Calibration
(temperature) touches validation only; test — original and shifted — is
scored once per seed. No tuning on test, no held-out peeking.
"""
import numpy as np

CORRUPTIONS = (
    {'name': 'gaussian-noise-s1', 'family': 'noise', 'severity': 1,
     'sigma': 1.5},
    {'name': 'gaussian-noise-s2', 'family': 'noise', 'severity': 2,
     'sigma': 3.0},
    {'name': 'occlude-s1', 'family': 'occlusion', 'severity': 1,
     'size': 4},
    {'name': 'occlude-s2', 'family': 'occlusion', 'severity': 2,
     'size': 8},
    {'name': 'roll-s1', 'family': 'roll', 'severity': 1, 'shift': 2},
    {'name': 'roll-s2', 'family': 'roll', 'severity': 2, 'shift': 4},
)
SEEDS = (0, 1, 2)


def apply(images, spec, seed=0):
    """Corrupt a batch deterministically; unknown spec raises."""
    rng = np.random.RandomState(seed)
    out = np.asarray(images, dtype=np.float64).copy()
    if spec['family'] == 'noise':
        out += rng.normal(0, spec['sigma'], size=out.shape)
    elif spec['family'] == 'occlusion':
        size = spec['size']
        height, width = out.shape[1], out.shape[2]
        top = rng.randint(0, height - size + 1)
        left = rng.randint(0, width - size + 1)
        out[:, top:top + size, left:left + size] = 0.0
    elif spec['family'] == 'shift':
        out += spec['delta']
    elif spec['family'] == 'roll':
        out = np.roll(out, shift=spec['shift'], axis=2)
    else:
        raise ValueError('unknown corruption family %r' % spec['family'])
    return out.astype(np.float32)


def names():
    """Predeclared corruption names in study order."""
    return [spec['name'] for spec in CORRUPTIONS]
