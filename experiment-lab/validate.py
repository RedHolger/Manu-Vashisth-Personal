"""Statistical validation for ExperimentLab (P07-02): predeclared A/A and
alternative-effect simulation studies with Monte Carlo uncertainty.

The seeds below are HELD OUT: they never appear in the reference, the tests
or any development run. Changing them after seeing results would be tuning;
they are constants so a rerun reproduces the exact published numbers.
"""
import math

from project import analyze, simulate

# Held-out simulation seeds. Seed 7 (and its neighbours) belong to the
# reference and the contract tests; these ranges never overlap them.
AA_SEEDS = tuple(range(1000, 1500))       # 500 A/A runs, true effect 0
EFFECT_SEEDS = tuple(range(2000, 2200))   # 200 runs, true effect 0.2
PERMUTATIONS = 199
N_PER_RUN = 200
ALPHA = 0.05
EFFECT_SIZE = 0.2


def monte_carlo_se(rate, repetitions):
    """Standard error of an observed frequency; zero at the boundaries."""
    if repetitions < 1:
        raise ValueError('repetitions required')
    return math.sqrt(rate * (1.0 - rate) / repetitions)


def _study(seeds, effect):
    rejections, covered = 0, 0
    for seed in seeds:
        result = analyze(simulate(seed=seed, n=N_PER_RUN, effect=effect),
                         seed=seed, permutations=PERMUTATIONS)
        if result['randomization_p'] < ALPHA:
            rejections += 1
        low, high = result['normal_approx_95_interval']
        if low <= effect <= high:
            covered += 1
    return {'runs': len(seeds),
            'rejections': rejections,
            'rate': rejections / len(seeds),
            'se': monte_carlo_se(rejections / len(seeds), len(seeds)),
            'covered': covered,
            'coverage': covered / len(seeds)}


def aa_study():
    """Null world: every rejection is a false positive by construction."""
    outcome = _study(AA_SEEDS, 0.0)
    return {'kind': 'A/A', 'true_effect': 0.0,
            'alpha': ALPHA, 'permutations': PERMUTATIONS,
            'n_per_run': N_PER_RUN, 'seed_first': AA_SEEDS[0],
            'seed_last': AA_SEEDS[-1],
            'false_positive_rate': outcome['rate'],
            'false_positive_se': outcome['se'],
            'interval_coverage': outcome['coverage'],
            'interval_coverage_se': monte_carlo_se(outcome['coverage'],
                                                   outcome['runs']),
            'runs': outcome['runs']}


def effect_study():
    """Alternative world: rejections estimate power, coverage still applies."""
    outcome = _study(EFFECT_SEEDS, EFFECT_SIZE)
    return {'kind': 'alternative-effect', 'true_effect': EFFECT_SIZE,
            'alpha': ALPHA, 'permutations': PERMUTATIONS,
            'n_per_run': N_PER_RUN, 'seed_first': EFFECT_SEEDS[0],
            'seed_last': EFFECT_SEEDS[-1],
            'power': outcome['rate'],
            'power_se': outcome['se'],
            'interval_coverage': outcome['coverage'],
            'interval_coverage_se': monte_carlo_se(outcome['coverage'],
                                                   outcome['runs']),
            'runs': outcome['runs']}
