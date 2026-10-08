"""P18-02/03/04: confined lab, verified cleanup, honest scoring, no hardware."""
import unittest

import checks
import evaluate
import faultlab
import physical
from faultlab import Lab, LabRefused


class ConfinementTests(unittest.TestCase):
    def test_refuses_root_home_and_outside(self):
        import os
        self.assertTrue(Lab.refuse('/'))
        self.assertTrue(Lab.refuse(os.path.expanduser('~')))
        self.assertTrue(Lab.refuse('/etc'))
        self.assertTrue(Lab.refuse('/usr/bin'))

    def test_lab_root_confined_to_temp(self):
        lab = Lab('confine')
        try:
            self.assertFalse(Lab.refuse(str(lab.root)))
            manifest = lab.manifest()
            self.assertTrue(manifest['confined'])
        finally:
            lab.cleanup()


class FaultLabTests(unittest.TestCase):
    def test_disk_exhaustion_setup_and_cleanup(self):
        lab = Lab('disk')
        try:
            quota = lab.seed_disk_exhaustion()
            self.assertEqual(quota['status'], 'FAIL')
        finally:
            report = lab.cleanup()
        self.assertTrue(report['root_removed'])
        self.assertTrue(report['cleaned'])

    def test_killed_service_setup_and_cleanup(self):
        lab = Lab('kill')
        try:
            state = lab.seed_killed_service()
            self.assertEqual(state['status'], 'FAIL')
            self.assertEqual(
                checks.process(pid=state['pid'])['status'], 'FAIL')
        finally:
            report = lab.cleanup()
        self.assertTrue(report['cleaned'])

    def test_dns_failure_stateless(self):
        lab = Lab('dns')
        try:
            state = lab.seed_dns_failure()
            self.assertEqual(state['status'], 'FAIL')
        finally:
            self.assertTrue(lab.cleanup()['cleaned'])

    def test_cpu_pressure_bounded_and_reaped(self):
        lab = Lab('cpu')
        try:
            load = lab.seed_cpu_pressure(seconds=2, workers=2)
            self.assertIn(load['status'], ('PASS', 'WARN', 'UNKNOWN'))
            self.assertIn('load_1_5_15', load)
        finally:
            report = lab.cleanup()
        self.assertTrue(report['cleaned'])
        self.assertEqual(report['unkilled_pids'], [])


class EvaluationTests(unittest.TestCase):
    def test_full_matrix_localizes(self):
        cases = [evaluate.run_case(f) for f in (
            'disk-exhaustion', 'killed-service', 'dns-failure',
            'cpu-pressure')]
        scored = evaluate.score(cases)
        self.assertEqual(scored['localized'], 4)
        self.assertEqual(scored['n_faults'], 4)
        self.assertIn('false_alarms', scored)
        self.assertIn('unknowns', scored)
        self.assertGreater(scored['collection_seconds_total'], 0)

    def test_report_hedged_no_certainty(self):
        cases = [evaluate.run_case('dns-failure')]
        text = evaluate.report(evaluate.score(cases))
        self.assertIn('consistent with', text)
        self.assertEqual(evaluate.certainty_scan(text), [])
        self.assertIn('Next step', text)

    def test_physical_blocked_no_hardware_claims(self):
        self.assertEqual(physical.probe_spare()['status'], 'BLOCKED')
        work = physical.hardware_work_performed()
        self.assertEqual(work['machines_touched'], 0)
        self.assertIn('No hardware work', work['statement'])
        self.assertEqual(physical.hardware_claim_scan('results'), [])

    def test_scanner_catches_affirmative_plant_not_negation(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'honest.md').write_text(
                'No claim of server repair is made here.\n')
            self.assertEqual(physical.hardware_claim_scan(tmp), [])
            Path(tmp, 'bad.md').write_text(
                'Server repair complete. Hardware fixed.\n')
            hits = physical.hardware_claim_scan(tmp)
            self.assertTrue(hits)


if __name__ == '__main__':
    unittest.main()
