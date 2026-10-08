"""P07-01: hand-computable fixtures validate every denominator and rule."""
import unittest

from experiment import (assign_arm, connect, extract_analysis_rows,
                        load_config, log_exposure, record_outcome)
from project import analyze

CONFIG = """\
unit: user
hypothesis: Checkout button color increases purchase rate
primary_metric: purchased
guardrails:
  - refund_rate
allocation:
  A: 0.5
  B: 0.5
horizon_days: 14
randomization_seed: 7
"""

HORIZON = '2026-01-15T00:00:00Z'
LATE = '2026-01-16T00:00:00Z'


def seeded():
    """Six users with a fully hand-computed fate (see test_hand_computed)."""
    conn = connect()
    for unit, arm in (('u1', 'A'), ('u2', 'A'), ('u3', 'B'),
                      ('u4', 'B'), ('u5', 'A'), ('u6', 'B')):
        log_exposure(conn, unit, arm, '2026-01-02T00:00:00Z', source='web')
    for unit, outcome, when in (('u1', 0, HORIZON), ('u2', 1, HORIZON),
                                ('u3', 1, HORIZON), ('u4', 1, HORIZON),
                                ('u5', 1, LATE)):
        record_outcome(conn, unit, outcome, when)
    return conn


class MetricContractTests(unittest.TestCase):
    def test_hand_computed_denominators(self):
        # u1..u4 analyze (A: 0,1  B: 1,1); u5 late-outcome excluded;
        # u6 exposed without outcome; ghost outcome without exposure.
        conn = seeded()
        record_outcome(conn, 'ghost', 1, HORIZON)
        bundle = extract_analysis_rows(conn, HORIZON)
        self.assertEqual(bundle['denominators'], {
            'exposed_units': 6,
            'analysis_rows': 4,
            'per_arm': {'A': 2, 'B': 2},
            'excluded_late_outcomes': 1,
            'outcomes_without_exposure': 1,
            'exposed_without_outcome': 1,
        })
        self.assertEqual(
            [(row['user'], row['arm'], row['outcome'])
             for row in bundle['rows']],
            [('u1', 'A', 0.0), ('u2', 'A', 1.0),
             ('u3', 'B', 1.0), ('u4', 'B', 1.0)])

    def test_hand_computed_effect_reaches_analysis(self):
        bundle = extract_analysis_rows(seeded(), HORIZON)
        result = analyze(bundle['rows'], seed=7, permutations=99)
        # mean(B) = 1.0, mean(A) = 0.5, by hand.
        self.assertEqual(result['effect_B_minus_A'], 0.5)
        self.assertEqual((result['n_A'], result['n_B']), (2, 2))

    def test_first_exposure_wins(self):
        conn = connect()
        self.assertTrue(log_exposure(conn, 'u1', 'A', HORIZON))
        self.assertFalse(log_exposure(conn, 'u1', 'B', HORIZON))
        record_outcome(conn, 'u1', 1, HORIZON)
        bundle = extract_analysis_rows(conn, HORIZON)
        self.assertEqual(bundle['rows'][0]['arm'], 'A')

    def test_first_outcome_wins(self):
        conn = connect()
        log_exposure(conn, 'u1', 'A', HORIZON)
        self.assertTrue(record_outcome(conn, 'u1', 0, HORIZON))
        self.assertFalse(record_outcome(conn, 'u1', 1, HORIZON))
        bundle = extract_analysis_rows(conn, HORIZON)
        self.assertEqual(bundle['rows'][0]['outcome'], 0.0)

    def test_horizon_boundary_is_inclusive(self):
        conn = connect()
        log_exposure(conn, 'u1', 'A', HORIZON)
        record_outcome(conn, 'u1', 1, HORIZON)
        self.assertEqual(
            extract_analysis_rows(conn, HORIZON)['denominators'][
                'analysis_rows'], 1)

    def test_config_loads(self):
        config = load_config(CONFIG)
        self.assertEqual(config['unit'], 'user')
        self.assertEqual(config['allocation'], {'A': 0.5, 'B': 0.5})
        self.assertEqual(config['guardrails'], ['refund_rate'])
        self.assertEqual(config['horizon_days'], 14)

    def test_config_rejects_lies(self):
        with self.assertRaises(ValueError):
            load_config(CONFIG.replace('horizon_days: 14', ''))
        with self.assertRaises(ValueError):
            load_config(CONFIG.replace('A: 0.5\n  B: 0.5',
                                       'A: 0.0\n  B: 0.0'))
        with self.assertRaises(ValueError):
            load_config(CONFIG.replace('horizon_days: 14',
                                       'horizon_days: soon'))
        with self.assertRaises(ValueError):
            load_config('unit: user\n\tunit: x\n')
        with self.assertRaises(ValueError):
            load_config(CONFIG + 'unit: device\n')

    def test_assignment_is_deterministic_and_split(self):
        allocation = {'A': 0.5, 'B': 0.5}
        arms = [assign_arm('user-%d' % index, allocation, seed=7)
                for index in range(10000)]
        self.assertEqual(
            [assign_arm('user-%d' % index, allocation, seed=7)
             for index in range(100)], arms[:100])
        share = arms.count('A') / len(arms)
        self.assertTrue(0.48 < share < 0.52, share)

    def test_bad_inputs_rejected(self):
        conn = connect()
        with self.assertRaises(ValueError):
            log_exposure(conn, 'u1', 'C', HORIZON)
        with self.assertRaises(ValueError):
            record_outcome(conn, 'u1', 'lots', HORIZON)


if __name__ == '__main__':
    unittest.main()
