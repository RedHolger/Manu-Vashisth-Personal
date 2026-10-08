"""P11-03: CI gate passes on repair, fails on seeded; live targets BLOCKED."""
import unittest

import lab_app
import regression
import runner
from regression import IntegrationBlocked, RegressionRunner, TargetAdapter


class GateTests(unittest.TestCase):
    def test_before_after_passes(self):
        result = RegressionRunner().before_after()
        self.assertEqual(result['gate'], 'PASS')
        self.assertGreater(result['before']['mismatches'], 0)
        self.assertEqual(result['after']['mismatches'], 0)
        self.assertTrue(result['oracle_unchanged'])

    def test_gate_fails_on_seeded_report(self):
        vuln = runner.evaluate(lab_app.VULNERABLE_BUGS, 'extended')
        self.assertEqual(RegressionRunner.gate_for(vuln), 'FAIL')

    def test_gate_passes_on_repaired_report(self):
        fixed = runner.evaluate(frozenset(), 'extended')
        self.assertEqual(RegressionRunner.gate_for(fixed), 'PASS')

    def test_oracle_move_voids_the_run(self):
        gate = RegressionRunner()
        real = regression.oracle_sha256
        try:
            regression.oracle_sha256 = lambda: 'tampered'
            with self.assertRaises(regression.OracleMovedError):
                gate.run_target(frozenset(), 'repaired')
        finally:
            regression.oracle_sha256 = real

    def test_no_credentials_in_either_report(self):
        result = RegressionRunner().before_after()
        self.assertTrue(regression.no_credentials(result['before']))
        self.assertTrue(regression.no_credentials(result['after']))

    def test_before_and_after_cover_the_full_matrix(self):
        result = RegressionRunner().before_after()
        self.assertEqual(result['before']['cases'], 22)
        self.assertEqual(result['after']['cases'], 22)


class LiveTargetTests(unittest.TestCase):
    def test_probe_reports_blocked_with_concrete_prerequisites(self):
        probe = TargetAdapter.probe()
        for target in TargetAdapter.LIVE_TARGETS:
            self.assertIn(target, probe)
            # In this offline environment every live target is BLOCKED;
            # the assertion is that the status is honest, never a fake READY.
            if probe[target]['status'] == 'BLOCKED':
                self.assertTrue(probe[target]['missing'])
            else:
                self.assertEqual(probe[target]['missing'], [])

    def test_provision_refuses_a_stand_in(self):
        for target in TargetAdapter.LIVE_TARGETS:
            with self.assertRaises(IntegrationBlocked):
                TargetAdapter.provision(target)


if __name__ == '__main__':
    unittest.main()
