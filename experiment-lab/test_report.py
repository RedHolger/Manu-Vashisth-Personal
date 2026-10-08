"""P07-03: SRM arithmetic, sensitivity bounds, guardrails and the refusal."""
import unittest

from report import (analysis_report, guardrails, sensitivity_bounds,
                    srm_check)

CONFIG = {'allocation': {'A': 0.5, 'B': 0.5}, 'min_per_arm': 2,
          'randomization_seed': 7}


def rows_for(outcomes_A, outcomes_B):
    rows = [{'user': 'a%d' % index, 'arm': 'A', 'outcome': value}
            for index, value in enumerate(outcomes_A)]
    rows += [{'user': 'b%d' % index, 'arm': 'B', 'outcome': value}
             for index, value in enumerate(outcomes_B)]
    return rows


class ReportTests(unittest.TestCase):
    def test_srm_balanced_passes(self):
        check = srm_check(500, 500, CONFIG['allocation'])
        self.assertAlmostEqual(check['statistic'], 0.0)
        self.assertAlmostEqual(check['p_value'], 1.0)
        self.assertTrue(check['passes'])

    def test_srm_imbalanced_fails(self):
        # chi2 = (600-500)^2/500 + (400-500)^2/500 = 40; p ~ 2.5e-10.
        check = srm_check(600, 400, CONFIG['allocation'])
        self.assertAlmostEqual(check['statistic'], 40.0)
        self.assertLess(check['p_value'], 0.001)
        self.assertFalse(check['passes'])

    def test_srm_rejects_empty(self):
        with self.assertRaises(ValueError):
            srm_check(0, 0, CONFIG['allocation'])

    def test_sensitivity_bounds_by_hand(self):
        # A: {0, 0}, B: {1, 1}; one missing aside.
        # Upper: B gains a 1, A gains a 0 -> 1.0 - 0.0 = 1.0.
        # Lower: B gains a 0, A gains a 1 -> 2/3 - 1/3 = 1/3.
        bounds = sensitivity_bounds(rows_for([0, 0], [1, 1]), 1, 1)
        self.assertAlmostEqual(bounds['upper'], 1.0)
        self.assertAlmostEqual(bounds['lower'], 1.0 / 3.0)
        self.assertEqual(bounds['range'], [0, 1])

    def test_sensitivity_none_missing(self):
        bounds = sensitivity_bounds(rows_for([0], [1]), 0, 0)
        self.assertEqual(
            (bounds['lower'], bounds['upper'], bounds['range']),
            (None, None, None))

    def test_guardrails_name_everything(self):
        denominators = {'per_arm': {'A': 100, 'B': 100}}
        srm = srm_check(100, 100, CONFIG['allocation'])
        rules = guardrails(CONFIG, denominators, srm, 0.0)
        self.assertTrue(all(rule['passed'] for rule in rules))
        blocked = guardrails(CONFIG, {'per_arm': {'A': 1, 'B': 100}}, srm,
                             0.5)
        self.assertEqual([rule['name'] for rule in blocked
                          if not rule['passed']],
                         ['min-per-arm', 'missing-share'])

    def test_randomized_clean_report_is_causal(self):
        rows = rows_for([0] * 50 + [1] * 50, [0] * 40 + [1] * 60)
        denominators = {'exposed_units': 200, 'per_arm': {'A': 100,
                                                         'B': 100}}
        report = analysis_report(rows, denominators, CONFIG, randomized=True)
        self.assertTrue(report['causal_claim'])
        self.assertAlmostEqual(report['effect_B_minus_A'], 0.1)
        self.assertEqual(report['blocked_by'], [])
        self.assertIn('random assignment', report['assumptions'])

    def test_srm_failure_blocks_causation(self):
        rows = rows_for([0] * 600, [1] * 400)
        denominators = {'exposed_units': 1000, 'per_arm': {'A': 600,
                                                          'B': 400}}
        report = analysis_report(rows, denominators, CONFIG, randomized=True)
        self.assertFalse(report['causal_claim'])
        self.assertIsNone(report['effect_B_minus_A'])
        self.assertEqual(report['blocked_by'], ['sample-ratio'])
        self.assertEqual(report['descriptive']['n_A'], 600)

    def test_nonrandomized_data_gets_no_causal_claim(self):
        rows = rows_for([0] * 50 + [1] * 50, [0] * 40 + [1] * 60)
        denominators = {'exposed_units': 200, 'per_arm': {'A': 100,
                                                         'B': 100}}
        report = analysis_report(rows, denominators, CONFIG,
                                 randomized=False)
        self.assertFalse(report['causal_claim'])
        self.assertIsNone(report['randomization_p'])
        self.assertIn('nonrandomized data', report['assumptions'][0])
        # ... but the descriptive facts are still reported.
        self.assertEqual(report['descriptive']['n_B'], 100)


if __name__ == '__main__':
    unittest.main()
