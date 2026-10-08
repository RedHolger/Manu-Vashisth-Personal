"""Analysis reporting for ExperimentLab (P07-03): sample-ratio checks,
missing-outcome sensitivity and guardrails around the reference estimate.

The rule this module enforces: a causal sentence appears in the report if
and only if the data came from the randomized assignment AND every blocking
guardrail passes. Anything else gets descriptive statistics plus an explicit
refusal to claim causation. The SRM check is a chi-square goodness-of-fit
against the planned allocation (df=1 survival via erfc — exact, no tables).
"""
import math

from project import analyze

# An SRM p-value below this blocks every causal sentence. 0.001 is the
# industry-standard alert line: far enough from 0.05 that a real imbalance
# trips it, close enough that noise rarely does.
SRM_ALPHA = 0.001
# Missing outcomes above this share block causal claims: beyond it the
# sensitivity bounds, not the point estimate, own the conclusion.
MAX_MISSING_SHARE = 0.20


def srm_check(n_A, n_B, allocation):
    """Chi-square goodness-of-fit of observed arm counts vs planned shares."""
    total = n_A + n_B
    if total < 1:
        raise ValueError('no randomized units to check')
    weights = [allocation['A'], allocation['B']]
    if sum(weights) <= 0:
        raise ValueError('allocation weights must total positively')
    expected = [total * weights[0] / sum(weights),
                total * weights[1] / sum(weights)]
    if min(expected) <= 0:
        raise ValueError('allocation gives an arm zero expectation')
    statistic = sum((observed - mean) ** 2 / mean
                    for observed, mean in zip((n_A, n_B), expected))
    p_value = math.erfc(math.sqrt(statistic / 2.0))
    return {'statistic': statistic, 'p_value': p_value,
            'passes': p_value >= SRM_ALPHA,
            'observed': {'A': n_A, 'B': n_B},
            'expected': {'A': expected[0], 'B': expected[1]}}


def sensitivity_bounds(rows, missing_A, missing_B):
    """Best/worst-case effect bounds imputing missing outcomes at extremes.

    With missing_A outcomes absent from arm A and missing_B from arm B, the
    effect is largest when A's missing are at the observed floor and B's at
    the ceiling, and smallest the other way round. Binary and continuous
    outcomes both work: the range is whatever was actually observed.
    """
    if missing_A < 0 or missing_B < 0:
        raise ValueError('missing counts cannot be negative')
    if missing_A == 0 and missing_B == 0:
        return {'lower': None, 'upper': None, 'range': None}
    observed = [row['outcome'] for row in rows]
    if not observed:
        raise ValueError('no observed outcomes to bound from')
    floor, ceiling = min(observed), max(observed)
    sums = {'A': sum(row['outcome'] for row in rows if row['arm'] == 'A'),
            'B': sum(row['outcome'] for row in rows if row['arm'] == 'B')}
    counts = {'A': sum(1 for row in rows if row['arm'] == 'A'),
              'B': sum(1 for row in rows if row['arm'] == 'B')}
    upper = ((sums['B'] + missing_B * ceiling) / (counts['B'] + missing_B)
             - (sums['A'] + missing_A * floor) / (counts['A'] + missing_A))
    lower = ((sums['B'] + missing_B * floor) / (counts['B'] + missing_B)
             - (sums['A'] + missing_A * ceiling) / (counts['A'] + missing_A))
    return {'lower': lower, 'upper': upper,
            'range': [floor, ceiling]}


def guardrails(config, denominators, srm, missing_share):
    """Every blocking rule, evaluated and named — no silent passes."""
    per_arm = denominators.get('per_arm', {})
    rules = [
        {'name': 'min-per-arm',
         'passed': min(per_arm.get('A', 0), per_arm.get('B', 0))
                   >= config.get('min_per_arm', 2),
         'detail': 'per-arm counts %s' % (per_arm,)},
        {'name': 'sample-ratio',
         'passed': bool(srm['passes']),
         'detail': 'chi2=%.3f p=%.5f' % (srm['statistic'], srm['p_value'])},
        {'name': 'missing-share',
         'passed': missing_share <= MAX_MISSING_SHARE,
         'detail': 'missing share %.3f (limit %.2f)'
                   % (missing_share, MAX_MISSING_SHARE)},
    ]
    return rules


def analysis_report(rows, denominators, config, randomized=True,
                    missing_A=0, missing_B=0):
    """Estimate with assumptions — or descriptive statistics with a refusal.

    `missing_A`/`missing_B` are counts of exposed units without an outcome in
    each arm; the caller passes them from the extraction denominators (a zero
    default means the caller states nothing is missing, and the guardrail
    below holds them to it).
    """
    estimate = analyze(rows, seed=config.get('randomization_seed', 7),
                       permutations=199)
    srm = srm_check(estimate['n_A'], estimate['n_B'],
                    config['allocation'])
    exposed = denominators.get('exposed_units', estimate['n_A']
                               + estimate['n_B'])
    missing_share = ((missing_A + missing_B) / exposed if exposed else 1.0)
    rules = guardrails(config, denominators, srm, missing_share)
    bounds = sensitivity_bounds(rows, missing_A, missing_B)
    blocked = [rule['name'] for rule in rules if not rule['passed']]
    causal = bool(randomized) and not blocked
    return {
        'randomized': bool(randomized),
        'causal_claim': causal,
        'effect_B_minus_A': estimate['effect_B_minus_A'] if causal else None,
        'interval_95': estimate['normal_approx_95_interval'] if causal
                       else None,
        'randomization_p': estimate['randomization_p'] if causal else None,
        'descriptive': {
            'n_A': estimate['n_A'], 'n_B': estimate['n_B'],
            'allocation_p_normal_approx':
                estimate['allocation_p_normal_approx'],
        },
        'srm': srm,
        'missing_share': missing_share,
        'sensitivity_bounds': bounds,
        'guardrails': rules,
        'blocked_by': blocked,
        'assumptions': estimate['assumptions'] if causal else
                       ['no causal interpretation: %s'
                        % ('nonrandomized data' if not randomized
                           else 'blocked guardrails: ' + ', '.join(blocked))],
    }
