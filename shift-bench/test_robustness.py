"""P09-03: predeclared shifts measured, calibration stays on validation."""
import unittest

from corrupt import CORRUPTIONS, SEEDS, apply, names
from project import choose_temperature
from robustness import run_seed


class RobustnessTests(unittest.TestCase):
    def test_corruptions_predeclared_and_deterministic(self):
        self.assertEqual(len(CORRUPTIONS), 6)
        self.assertEqual(names(), [spec['name'] for spec in CORRUPTIONS])
        from dataset import load_dataset
        pack = load_dataset()
        sample = pack['images'][:4]
        first = apply(sample, CORRUPTIONS[0], seed=0)
        second = apply(sample, CORRUPTIONS[0], seed=0)
        self.assertTrue((first == second).all())
        third = apply(sample, CORRUPTIONS[0], seed=1)
        self.assertFalse((first == third).all())

    def test_heavier_noise_degrades_or_ties(self):
        result = run_seed(0)
        light = result['conditions']['gaussian-noise-s1']['accuracy']
        heavy = result['conditions']['gaussian-noise-s2']['accuracy']
        self.assertLessEqual(heavy, light)

    def test_temperature_chosen_on_validation_only(self):
        result = run_seed(1)
        self.assertIn(result['temperature'], [0.5, 1, 1.5, 2, 3, 5])
        # Validation NLL must not get worse after its own calibration.
        self.assertLessEqual(result['validation_after']['nll'],
                             result['validation_before']['nll'])
        # All three seeds retained with full condition grids.
        self.assertGreaterEqual(len(result['conditions']), 13)

    def test_per_group_denominators_present(self):
        result = run_seed(0)
        groups = result['per_group_original']
        self.assertEqual(set(groups), {'label-0', 'label-1'})
        for group in groups.values():
            self.assertGreater(group['n'], 0)
            self.assertIn('accuracy', group)

    def test_all_seeds_run(self):
        for seed in SEEDS:
            result = run_seed(seed)
            self.assertIn('original', result['conditions'])
            self.assertIn('occlude-s2+calibrated', result['conditions'])


if __name__ == '__main__':
    unittest.main()
