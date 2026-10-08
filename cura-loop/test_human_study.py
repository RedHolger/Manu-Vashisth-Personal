"""P10-04: measured human time is kept strictly separate from synthetic cost."""
import unittest

from human_study import (AnnotationSession, CostMixingError, HumanStudy,
                         SyntheticProxyCost, time_action, STATUS_BLOCKED,
                         STATUS_MEASURED)


def _busy(millis=1):
    import time
    end = time.perf_counter() + millis / 1000.0
    while time.perf_counter() < end:
        pass
    return 'done'


class TimingHarnessTests(unittest.TestCase):
    def test_time_action_returns_positive_elapsed(self):
        result, elapsed = time_action(_busy, 2)
        self.assertEqual(result, 'done')
        self.assertGreater(elapsed, 0.0)

    def test_dry_run_session_is_not_human_data(self):
        session = AnnotationSession('dry-run', consent=None)
        record = session.record_label('x', 1, action=lambda: _busy(1))
        self.assertEqual(record['source'], 'dry-run-stopwatch')
        self.assertEqual(session.labels_measured, 0)
        self.assertEqual(session.measured_human_seconds, 0.0)
        self.assertEqual(len(session.dry_run_records), 1)

    def test_consented_session_measures_human_time(self):
        consent = {'granted': True, 'form': 'v1', 'at': 123.0}
        session = AnnotationSession('alice', consent=consent)
        session.record_label('x', 1, action=lambda: _busy(1))
        self.assertTrue(session.has_consent)
        self.assertEqual(session.labels_measured, 1)
        self.assertGreater(session.measured_human_seconds, 0.0)
        self.assertEqual(session.records[0]['source'], 'stopwatch')


class HumanStudyTests(unittest.TestCase):
    def test_no_participants_is_blocked(self):
        study = HumanStudy(proxy=SyntheticProxyCost(2.0))
        study.add_session(AnnotationSession('dry-run', consent=None)
                          ).record_label('x', 1, action=lambda: _busy(1))
        self.assertEqual(study.participants_measured, 0)
        self.assertEqual(study.status(), STATUS_BLOCKED)

    def test_consenting_participant_is_measured(self):
        study = HumanStudy(proxy=SyntheticProxyCost(2.0))
        s = study.add_session(
            AnnotationSession('alice', consent={'granted': True}))
        s.record_label('x', 1, action=lambda: _busy(1))
        self.assertEqual(study.participants_measured, 1)
        self.assertEqual(study.status(), STATUS_MEASURED)

    def test_measured_and_proxy_are_distinct_fields(self):
        study = HumanStudy(proxy=SyntheticProxyCost(3.0))
        s = study.add_session(
            AnnotationSession('alice', consent={'granted': True}))
        s.record_label('x', 1, action=lambda: _busy(1))
        report = study.report()
        self.assertEqual(report['measured_human_time']['source'], 'stopwatch')
        self.assertEqual(report['synthetic_proxy_cost']['source'], 'simulation')
        self.assertIn('measured_human_time', report)
        self.assertIn('synthetic_proxy_cost', report)

    def test_combined_cost_is_refused(self):
        study = HumanStudy()
        with self.assertRaises(CostMixingError):
            study.combined_cost()

    def test_proxy_cost_scales_with_labels(self):
        proxy = SyntheticProxyCost(2.5)
        self.assertEqual(proxy.for_labels(4),
                         {'seconds': 10.0, 'source': 'simulation',
                          'n_labels': 4})


if __name__ == '__main__':
    unittest.main()
