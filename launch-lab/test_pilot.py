"""P17-02: ordered/time-windowed instrumentation; tests separated from users."""
import unittest

import pilot


class PilotTests(unittest.TestCase):
    def test_readiness_emits_ordered_events(self):
        run = pilot.readiness_check({'files': ['a'], 'gate': True},
                                    's1', at=1000.0)
        self.assertTrue(run['ok'])
        self.assertEqual([e['type'] for e in run['events']],
                         ['started', 'checked', 'completed'])
        self.assertEqual([e['at'] for e in run['events']],
                         [1000.0, 1001.0, 1002.0])

    def test_windowed_funnel_counts_ordered_in_window(self):
        run = pilot.readiness_check({'files': ['a'], 'gate': True},
                                    's1', at=1000.0)
        out = pilot.windowed_funnel(
            [{**e, 'user': 't1'} for e in run['events']], window_s=3600)
        self.assertEqual(out['test']['completed'], 1)
        self.assertEqual(out['real_users'], 0)
        self.assertEqual(out['excluded'], [])

    def test_out_of_order_excluded_with_reason(self):
        events = [{'id': 's-completed', 'session': 's', 'user': 't',
                   'type': 'completed', 'at': 1000.0, 'test_account': True}]
        out = pilot.windowed_funnel(events)
        self.assertEqual(out['test']['completed'], 0)
        self.assertTrue(any('predecessor' in e['reason']
                            for e in out['excluded']))

    def test_late_events_excluded(self):
        events = [{'id': 's-started', 'session': 's', 'user': 't',
                   'type': 'started', 'at': 0.0, 'test_account': True},
                  {'id': 's-checked', 'session': 's', 'user': 't',
                   'type': 'checked', 'at': 10.0, 'test_account': True},
                  {'id': 's-completed', 'session': 's', 'user': 't',
                   'type': 'completed', 'at': 99999.0, 'test_account': True}]
        out = pilot.windowed_funnel(events, window_s=60)
        self.assertEqual(out['test']['completed'], 0)
        self.assertTrue(any('window' in e['reason'] for e in out['excluded']))

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            pilot.windowed_funnel([{'id': 'x', 'session': 's', 'user': 't',
                                    'type': 'purchase', 'at': 0.0,
                                    'test_account': True}])


if __name__ == '__main__':
    unittest.main()
