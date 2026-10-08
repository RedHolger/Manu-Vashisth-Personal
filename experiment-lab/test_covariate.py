"""P07-04: OLS arithmetic by hand, fallbacks open, gains on shared data."""
import unittest

from covariate import compare_methods, ols_adjust


def hand_rows():
    # y = arm + x exactly: (d, x, y) in {(0,0,0), (0,2,2), (1,0,1), (1,2,3)}.
    return [{'user': 'u%d' % index, 'arm': arm, 'x': x, 'outcome': y}
            for index, (arm, x, y) in enumerate(
                [('A', 0, 0), ('A', 2, 2), ('B', 0, 1), ('B', 2, 3)])]


class CovariateTests(unittest.TestCase):
    def test_ols_recovers_exact_coefficients(self):
        result = ols_adjust(hand_rows())
        self.assertAlmostEqual(result['ate'], 1.0)
        self.assertAlmostEqual(result['se'], 0.0)
        self.assertEqual(result['dof'], 1)

    def test_compare_prefers_adjusted_on_prognostic_data(self):
        import random
        rng = random.Random(11)
        rows = [{'user': str(index),
                 'arm': 'B' if index % 2 else 'A',
                 'x': (x := rng.gauss(0, 1)),
                 'outcome': x + (0.5 if index % 2 else 0.0)
                 + rng.gauss(0, 0.1)}
                for index in range(60)]
        comparison = compare_methods(rows)
        self.assertEqual(comparison['adjusted']['method'], 'ols-covariate')
        self.assertLess(comparison['adjusted']['se'],
                        comparison['baseline']['se'])
        self.assertLess(comparison['variance_ratio'], 1.0)

    def test_constant_covariate_falls_back_openly(self):
        rows = [{'user': str(index), 'arm': 'B' if index % 2 else 'A',
                 'x': 3.0, 'outcome': float(index % 3)}
                for index in range(8)]
        comparison = compare_methods(rows)
        self.assertEqual(comparison['adjusted']['method'],
                         'unadjusted-fallback')
        self.assertIn('constant', comparison['adjusted']['reason'])
        self.assertEqual(comparison['variance_ratio'], 1.0)

    def test_missing_covariate_falls_back_openly(self):
        rows = [{'user': str(index), 'arm': 'B' if index % 2 else 'A',
                 'outcome': float(index)} for index in range(8)]
        comparison = compare_methods(rows)
        self.assertEqual(comparison['adjusted']['method'],
                         'unadjusted-fallback')
        self.assertIn('missing', comparison['adjusted']['reason'])

    def test_too_few_rows_falls_back_openly(self):
        rows = [{'user': 'a', 'arm': 'A', 'x': 0.0, 'outcome': 0.0},
                {'user': 'b', 'arm': 'B', 'x': 1.0, 'outcome': 1.0}]
        with self.assertRaises(ValueError):
            ols_adjust(rows)

    def test_results_are_deterministic(self):
        self.assertEqual(compare_methods(hand_rows()),
                         compare_methods(hand_rows()))


if __name__ == '__main__':
    unittest.main()
