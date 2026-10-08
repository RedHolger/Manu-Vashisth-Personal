"""P08-01: Python and SQL agree on tiny boundary fixtures."""
import unittest

from ingest import connect, ingest
from metrics import sql_cohorts
from project import cohorts

ASOF = '2026-01-20T00:00:00Z'


def event(id_, user, kind, at, ingested=None):
    return {'id': id_, 'user': user, 'type': kind, 'at': at,
            'ingested_at': ingested or at}


def both(events, asof=ASOF):
    """The same events through the Python kernel and the SQL store."""
    conn = connect()
    ingest(conn, events)
    return cohorts(events, asof)['cohorts'], sql_cohorts(conn, asof)


class DataContractTests(unittest.TestCase):
    def test_hand_computed_fixture(self):
        # u1 signs Mon Jan 5, activates day 1, active day 8: full funnel.
        # u2 signs the same Monday, never activates, active day 15: out.
        events = [
            event('1', 'u1', 'signup', '2026-01-05T10:00:00Z'),
            event('2', 'u1', 'activate', '2026-01-06T10:00:00Z'),
            event('3', 'u1', 'active', '2026-01-13T10:00:00Z'),
            event('4', 'u2', 'signup', '2026-01-05T11:00:00Z'),
            event('5', 'u2', 'active', '2026-01-20T11:00:00Z'),
        ]
        expected = {'2026-01-05': {'users': 2, 'activated': 1,
                                   'week1_eligible': 2, 'week1_retained': 1,
                                   'week1_retention': 0.5}}
        python, sql = both(events)
        self.assertEqual(python, expected)
        self.assertEqual(sql, expected)

    def test_late_arrival_and_duplicate(self):
        # The reference kernel case: identical repeat collapses, the event
        # ingested after the cutoff never happened as far as metrics care.
        a = event('1', 'u1', 'signup', '2026-01-01T00:00:00Z')
        b = event('2', 'u1', 'active', '2026-01-09T00:00:00Z',
                  '2026-02-01T00:00:00Z')
        python, sql = both([a, a, b])
        self.assertEqual(python, sql)
        group = python['2025-12-29']
        self.assertEqual(group['users'], 1)
        # Eligible (asof past signup+14d) but the only activity arrived
        # after the cutoff: retained 0 of 1, a zero — not an unknown.
        self.assertEqual(group['week1_retention'], 0.0)

    def test_timezone_boundary_and_offsets(self):
        # Sunday 23:30 UTC stays in the Dec-29 Monday cohort; an event stamped
        # 03:30 +02:00 is 01:30 UTC Monday and lands in Jan-5.
        events = [
            event('1', 'u3', 'signup', '2026-01-04T23:30:00+00:00'),
            event('2', 'u4', 'signup', '2026-01-05T03:30:00+02:00'),
        ]
        python, sql = both(events, asof='2026-03-01T00:00:00Z')
        self.assertEqual(set(python), {'2025-12-29', '2026-01-05'})
        self.assertEqual(python, sql)
        for group in python.values():
            self.assertEqual(group['week1_retention'], 0.0)

    def test_conflicting_duplicate_rejected_both_layers(self):
        a = event('1', 'u1', 'signup', '2026-01-01T00:00:00Z')
        b = dict(a, type='active')
        with self.assertRaises(ValueError):
            cohorts([a, b], ASOF)
        with self.assertRaises(ValueError):
            ingest(connect(), [a, b])

    def test_schema_violations_rejected(self):
        conn = connect()
        naive = event('1', 'u1', 'signup', '2026-01-01T00:00:00')
        with self.assertRaises(ValueError):
            ingest(conn, [naive])
        extra = dict(event('1', 'u1', 'signup', '2026-01-01T00:00:00Z'),
                     session='s1')
        with self.assertRaises(ValueError):
            ingest(conn, [extra])
        empty = dict(event('1', '', 'signup', '2026-01-01T00:00:00Z'))
        with self.assertRaises(ValueError):
            ingest(conn, [empty])

    def test_empty_store_agrees(self):
        self.assertEqual(both([]), ({}, {}))

    def test_ingest_report_counts(self):
        conn = connect()
        a = event('1', 'u1', 'signup', '2026-01-01T00:00:00Z')
        report = ingest(conn, [a, a])
        self.assertEqual(report, {'stored': 1, 'duplicates': 1,
                                 'conflicts': 0})


if __name__ == '__main__':
    unittest.main()
