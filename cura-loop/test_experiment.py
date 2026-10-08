"""P10-03: fair comparison — matched seed/pool/budget, selection ignores test."""
import unittest

import experiment
from experiment import (average_curve, curves_to_csv, render_svg, run_method,
                        summarize)


class FairComparisonTests(unittest.TestCase):
    def test_matched_initial_pool_across_methods(self):
        seed, budget = 0, 20
        runs = {m: run_method(m, seed, budget) for m in experiment.METHODS}
        initials = [tuple(r['initial_ids']) for r in runs.values()]
        self.assertEqual(len(set(initials)), 1)     # identical across methods
        self.assertEqual(len(initials[0]), 5)

    def test_matched_budget_and_acquired_counts(self):
        seed, budget = 1, 25
        runs = [run_method(m, seed, budget) for m in experiment.METHODS]
        self.assertTrue(all(r['budget'] == budget for r in runs))
        self.assertTrue(all(r['acquired'] == budget for r in runs))

    def test_selection_never_sees_test_id(self):
        for seed in (0, 2):
            for method in experiment.METHODS:
                run = run_method(method, seed, 20)
                self.assertFalse(run['selection_saw_test_id'])

    def test_curve_is_monotonic_and_length_matches(self):
        run = run_method('uncertainty', 0, 30)
        xs = [p['labels_acquired'] for p in run['curve']]
        self.assertEqual(xs, list(range(1, run['acquired'] + 1)))
        for p in run['curve']:
            self.assertGreaterEqual(p['test_accuracy'], 0.0)
            self.assertLessEqual(p['test_accuracy'], 1.0)

    def test_determinism_same_seed_same_curve(self):
        a = run_method('random', 3, 20)
        b = run_method('random', 3, 20)
        self.assertEqual(a['curve'], b['curve'])
        self.assertEqual(a['final_accuracy'], b['final_accuracy'])

    def test_pool_and_test_hashes_match_across_methods(self):
        seed = 0
        runs = [run_method(m, seed, 15) for m in experiment.METHODS]
        self.assertEqual(len({r['pool_sha256'] for r in runs}), 1)
        self.assertEqual(len({r['test_sha256'] for r in runs}), 1)


class AggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exp = experiment.run_experiment(seeds=(0, 1), budget=20)

    def test_average_curve_shape(self):
        curve = average_curve(self.exp, 'uncertainty')
        self.assertTrue(curve)
        self.assertTrue(all(p['n_seeds'] == 2 for p in curve))
        self.assertEqual([p['labels_acquired'] for p in curve],
                         list(range(1, len(curve) + 1)))

    def test_summarize_reports_variability(self):
        summary = summarize(self.exp)
        self.assertEqual(set(summary), set(experiment.METHODS))
        for method, row in summary.items():
            self.assertEqual(row['n_seeds'], 2)
            self.assertGreaterEqual(row['final_accuracy_std'], 0.0)
            self.assertEqual(len(row['per_seed_final']), 2)

    def test_csv_has_a_row_per_point(self):
        text = curves_to_csv(self.exp)
        lines = [ln for ln in text.splitlines() if ln]
        expected = sum(len(r['curve']) for r in self.exp['runs'])
        self.assertEqual(len(lines) - 1, expected)      # minus header
        self.assertTrue(lines[0].startswith(
            'method,seed,labels_acquired,test_accuracy'))

    def test_svg_renders_one_polyline_per_method(self):
        svg = render_svg(self.exp)
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.rstrip().endswith('</svg>'))
        self.assertEqual(svg.count('<polyline'), len(experiment.METHODS))
        for method in experiment.METHODS:
            self.assertIn(method, svg)


if __name__ == '__main__':
    unittest.main()
