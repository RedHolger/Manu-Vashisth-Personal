"""Covariate adjustment for ExperimentLab (P07-04): OLS on a predeclared
covariate, compared against the fixed difference-in-means baseline on the
same estimand and the same simulated datasets.

The method is CUPED in spirit: regress the outcome on the arm indicator and
one pre-randomization covariate, read the arm coefficient as the adjusted
ATE. When the covariate carries no signal the adjustment is skipped openly —
a fallback recorded with its reason, never a silent switch of method.
"""
import math
import statistics


def _invert_3x3(matrix):
    """Gauss-Jordan inverse with partial pivoting; raises on singularity."""
    rows = [list(row) + [1.0 if i == j else 0.0 for j in range(3)]
            for i, row in enumerate(matrix)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda r: abs(rows[r][column]))
        if abs(rows[pivot][column]) < 1e-12:
            raise ValueError('singular design matrix')
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [value / scale for value in rows[column]]
        for other in range(3):
            if other != column:
                factor = rows[other][column]
                rows[other] = [a - factor * b for a, b
                               in zip(rows[other], rows[column])]
    return [row[3:] for row in rows]


def ols_adjust(rows):
    """Adjusted ATE via OLS on (intercept, arm, covariate).

    Each row needs `arm` in ('A','B'), numeric `outcome` and numeric `x`
    measured before randomization. Returns the arm coefficient, its standard
    error, and the residual degrees of freedom — or raises ValueError when
    the design is singular, in which case the caller falls back openly.
    """
    points = [(1.0 if row['arm'] == 'B' else 0.0, row['x'], row['outcome'])
              for row in rows]
    n = len(points)
    if n < 4:
        raise ValueError('need at least 4 rows for 3 coefficients')
    xs = [x for _, x, _ in points]
    if max(xs) == min(xs):
        raise ValueError('covariate is constant: no adjustment possible')
    xtx = [[0.0] * 3 for _ in range(3)]
    xty = [0.0] * 3
    for arm, covariate, outcome in points:
        features = (1.0, arm, covariate)
        for i in range(3):
            xty[i] += features[i] * outcome
            for j in range(3):
                xtx[i][j] += features[i] * features[j]
    inverse = _invert_3x3(xtx)
    coeffs = [sum(inverse[i][j] * xty[j] for j in range(3))
              for i in range(3)]
    fitted = [coeffs[0] + coeffs[1] * arm + coeffs[2] * covariate
              for arm, covariate, _ in points]
    residuals = [row['outcome'] - fit
                 for row, fit in zip(rows, fitted)]
    dof = n - 3
    sigma2 = sum(r * r for r in residuals) / dof
    se = math.sqrt(max(sigma2, 0.0) * inverse[1][1])
    mean_outcome = statistics.mean([row['outcome'] for row in rows])
    total_ss = sum((row['outcome'] - mean_outcome) ** 2 for row in rows)
    return {'ate': coeffs[1], 'se': se, 'dof': dof,
            'r_squared': 1.0 - sum(r * r for r in residuals) / total_ss
            if total_ss > 0 else 0.0}


def compare_methods(rows):
    """Baseline and adjusted estimates on the SAME rows, same estimand.

    Returns both point estimates with standard errors, the method actually
    used for the adjusted leg, and why if it fell back.
    """
    if any('x' not in row or row['x'] is None
           or not isinstance(row['x'], (int, float)) for row in rows):
        return _fallback(rows, 'covariate missing or non-numeric')
    try:
        adjusted = ols_adjust(rows)
    except ValueError as exc:
        return _fallback(rows, str(exc))
    base = _unadjusted(rows)
    return {'baseline': base,
            'adjusted': {'ate': adjusted['ate'], 'se': adjusted['se'],
                         'method': 'ols-covariate', 'r_squared':
                         adjusted['r_squared']},
            'variance_ratio': (adjusted['se'] ** 2 / base['se'] ** 2
                               if base['se'] > 0 else None)}


def _unadjusted(rows):
    a = [row['outcome'] for row in rows if row['arm'] == 'A']
    b = [row['outcome'] for row in rows if row['arm'] == 'B']
    effect = statistics.mean(b) - statistics.mean(a)
    se = math.sqrt(statistics.variance(a) / len(a)
                   + statistics.variance(b) / len(b))
    return {'ate': effect, 'se': se, 'method': 'difference-in-means'}


def _fallback(rows, reason):
    base = _unadjusted(rows)
    return {'baseline': base,
            'adjusted': {'ate': base['ate'], 'se': base['se'],
                         'method': 'unadjusted-fallback',
                         'reason': reason},
            'variance_ratio': 1.0}
