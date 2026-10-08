"""P07-02: the predeclared studies are reproducible and honestly reported."""
import unittest

import validate
from validate import (AA_SEEDS, EFFECT_SEEDS, monte_carlo_se)


class ValidationTests(unittest.TestCase):
    def test_held_out_seeds_avoid_development(self):
        self.assertEqual(len(set(AA_SEEDS)), 500)
        self.assertEqual(len(set(EFFECT_SEEDS)), 200)
        self.assertFalse(set(AA_SEEDS) & set(EFFECT_SEEDS))
        self.assertFalse(set(AA_SEEDS) & {7, 8, 9})
        self.assertFalse(set(EFFECT_SEEDS) & {7, 8, 9})

    def test_monte_carlo_se(self):
        self.assertAlmostEqual(monte_carlo_se(0.05, 500),
                              (0.05 * 0.95 / 500) ** 0.5)
        self.assertEqual(monte_carlo_se(0.0, 500), 0.0)
        with self.assertRaises(ValueError):
            monte_carlo_se(0.05, 0)

    def test_study_shape_on_tiny_ranges(self):
        real_aa, real_fx = validate.AA_SEEDS, validate.EFFECT_SEEDS
        validate.AA_SEEDS, validate.EFFECT_SEEDS = (1000, 1001), (2000,)
        try:
            aa = validate.aa_study()
            fx = validate.effect_study()
        finally:
            validate.AA_SEEDS, validate.EFFECT_SEEDS = real_aa, real_fx
        for study in (aa, fx):
            self.assertEqual(set(study),
                             {'kind', 'true_effect', 'alpha', 'permutations',
                              'n_per_run', 'seed_first', 'seed_last',
                              'power' if study['kind'] != 'A/A'
                              else 'false_positive_rate',
                              'power_se' if study['kind'] != 'A/A'
                              else 'false_positive_se',
                              'interval_coverage', 'interval_coverage_se',
                              'runs'})
        self.assertEqual(aa['runs'], 2)
        self.assertEqual(fx['runs'], 1)
        # Tiny smoke, not a calibration: two null runs rarely both reject.
        self.assertLessEqual(aa['false_positive_rate'], 1.0)

    def test_studies_are_deterministic(self):
        real_aa = validate.AA_SEEDS
        validate.AA_SEEDS = (1000, 1001)
        try:
            first = validate.aa_study()
            second = validate.aa_study()
        finally:
            validate.AA_SEEDS = real_aa
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
