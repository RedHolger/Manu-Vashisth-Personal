"""P08-02: segmentation, explicit windows, cohort-age filtering."""
import unittest

from ingest import connect, ingest, set_segments
from segments import (mature_only, segment_cohorts, sql_segment_cohorts)


def event(id_, user, kind, at, ingested=None):
    return {'id': id_, 'user': user, 'type': kind, 'at': at,
            'ingested_at': ingested or at}


def both(events, segments, asof, window=7):
    conn = connect()
    ingest(conn, events)
    set_segments(conn, segments)
    python = segment_cohorts(events, asof, segments, window)['cohorts']
    sql = sql_segment_cohorts(conn, asof, window)
    return python, sql


class SegmentTests(unittest.TestCase):
    def test_hand_computed_segments(self):
        events = [
            event('1', 'u1', 'signup', '2026-01-05T10:00:00Z'),
            event('2', 'u1', 'activate', '2026-01-06T10:00:00Z'),
            event('3', 'u1', 'active', '2026-01-13T10:00:00Z'),
            event('4', 'u2', 'signup', '2026-01-05T11:00:00Z'),
            event('5', 'u3', 'signup', '2026-01-05T12:00:00Z'),
            event('6', 'u3', 'activate', '2026-01-06T12:00:00Z'),
        ]
        segments = {'u1': 'organic', 'u2': 'paid'}
        # u3 has no mapping: stays 'unknown' as its own row.
        python, sql = both(events, segments, '2026-01-20T00:00:00Z')
        self.assertEqual(python, sql)
        self.assertEqual(
            python[('2026-01-05', 'organic')],
            {'users': 1, 'activated': 1, 'activation_eligible': 1,
             'activation_rate': 1.0, 'week1_eligible': 1,
             'week1_retained': 1, 'week1_retention': 1.0})
        self.assertEqual(
            python[('2026-01-05', 'paid')],
            {'users': 1, 'activated': 0, 'activation_eligible': 1,
             'activation_rate': 0.0, 'week1_eligible': 1,
             'week1_retained': 0, 'week1_retention': 0.0})
        self.assertEqual(python[('2026-01-05', 'unknown')]['users'], 1)
        self.assertEqual(
            python[('2026-01-05', 'unknown')]['activation_rate'], 1.0)

    def test_incomplete_activation_window_excluded(self):
        # Signup 2 days before the cutoff with a 7-day window: the user
        # counts in users but not in the activation denominator, and the
        # rate is None (unknown) — not zero.
        events = [event('1', 'u1', 'signup', '2026-01-18T10:00:00Z')]
        table = segment_cohorts(events, '2026-01-20T00:00:00Z',
                                {'u1': 'organic'})['cohorts']
        group = table[('2026-01-12', 'organic')]
        self.assertEqual(group['users'], 1)
        self.assertEqual(group['activation_eligible'], 0)
        self.assertIsNone(group['activation_rate'])
        self.assertEqual(group['activated'], 0)

    def test_incomplete_week1_excluded(self):
        # Old enough to complete activation but not week-1: activation has
        # a rate, week-1 stays unknown.
        events = [event('1', 'u1', 'signup', '2026-01-10T10:00:00Z'),
                  event('2', 'u1', 'activate', '2026-01-11T10:00:00Z')]
        table = segment_cohorts(events, '2026-01-20T00:00:00Z',
                                {'u1': 'organic'})['cohorts']
        group = table[('2026-01-05', 'organic')]
        self.assertEqual(group['activation_eligible'], 1)
        self.assertEqual(group['activation_rate'], 1.0)
        self.assertEqual(group['week1_eligible'], 0)
        self.assertIsNone(group['week1_retention'])

    def test_unknown_is_not_zero(self):
        events = [event('1', 'u9', 'signup', '2026-01-05T10:00:00Z')]
        python, sql = both(events, {}, '2026-01-20T00:00:00Z')
        self.assertIn(('2026-01-05', 'unknown'), python)
        self.assertEqual(python, sql)
        group = python[('2026-01-05', 'unknown')]
        self.assertEqual(group['users'], 1)
        # Unknown segment is a real row with real denominators, not a 0.
        self.assertEqual(group['activation_eligible'], 1)
        self.assertEqual(group['activation_rate'], 0.0)

    def test_explicit_window_changes_eligibility(self):
        events = [event('1', 'u1', 'signup', '2026-01-10T10:00:00Z'),
                  event('2', 'u1', 'activate', '2026-01-14T10:00:00Z')]
        narrow = segment_cohorts(events, '2026-01-20T00:00:00Z',
                                 {'u1': 'organic'},
                                 activation_window_days=3)['cohorts']
        wide = segment_cohorts(events, '2026-01-20T00:00:00Z',
                               {'u1': 'organic'},
                               activation_window_days=7)['cohorts']
        # Day-4 activation is inside a 7-day window but outside a 3-day one.
        self.assertEqual(narrow[('2026-01-05', 'organic')]['activated'], 0)
        self.assertEqual(wide[('2026-01-05', 'organic')]['activated'], 1)
        with self.assertRaises(ValueError):
            segment_cohorts(events, '2026-01-20T00:00:00Z', {}, 0)
        with self.assertRaises(ValueError):
            segment_cohorts(events, '2026-01-20T00:00:00Z', {}, 31)

    def test_mature_only_filters_young_cohorts(self):
        events = [event('1', 'old', 'signup', '2026-01-01T10:00:00Z'),
                  event('2', 'young', 'signup', '2026-01-18T10:00:00Z')]
        table = segment_cohorts(
            events, '2026-01-20T00:00:00Z',
            {'old': 'organic', 'young': 'organic'})['cohorts']
        mature = mature_only(table, 'week1')
        self.assertIn(('2025-12-29', 'organic'), mature)
        self.assertNotIn(('2026-01-12', 'organic'), mature)
        mature_act = mature_only(table, 'activation')
        self.assertIn(('2025-12-29', 'organic'), mature_act)
        self.assertNotIn(('2026-01-12', 'organic'), mature_act)

    def test_sql_agrees_on_mixed_ages(self):
        events = [
            event('1', 'u1', 'signup', '2026-01-01T10:00:00Z'),
            event('2', 'u1', 'activate', '2026-01-02T10:00:00Z'),
            event('3', 'u1', 'active', '2026-01-09T10:00:00Z'),
            event('4', 'u2', 'signup', '2026-01-18T10:00:00Z'),
        ]
        python, sql = both(events, {'u1': 'organic', 'u2': 'paid'},
                            '2026-01-20T00:00:00Z')
        self.assertEqual(python, sql)
        self.assertIsNone(
            python[('2026-01-12', 'paid')]['activation_rate'])
        self.assertIsNone(
            python[('2026-01-12', 'paid')]['week1_retention'])


if __name__ == '__main__':
    unittest.main()
