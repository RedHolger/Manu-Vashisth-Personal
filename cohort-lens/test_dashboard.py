"""P08-03: dashboard traces to source; memo refuses causal language."""
import re
import unittest
from pathlib import Path

from dashboard import build_dashboard
from segments import segment_cohorts

FIXTURE = [
    {'id': '1', 'user': 'u1', 'type': 'signup', 'at': '2026-01-05T10:00:00Z',
     'ingested_at': '2026-01-05T10:00:00Z'},
    {'id': '2', 'user': 'u1', 'type': 'activate', 'at': '2026-01-06T10:00:00Z',
     'ingested_at': '2026-01-06T10:00:00Z'},
    {'id': '3', 'user': 'u1', 'type': 'active', 'at': '2026-01-13T10:00:00Z',
     'ingested_at': '2026-01-13T10:00:00Z'},
    {'id': '4', 'user': 'u2', 'type': 'signup', 'at': '2026-01-05T11:00:00Z',
     'ingested_at': '2026-01-05T11:00:00Z'},
    {'id': '5', 'user': 'u3', 'type': 'signup', 'at': '2026-01-05T12:00:00Z',
     'ingested_at': '2026-01-05T12:00:00Z'},
    {'id': '6', 'user': 'u3', 'type': 'activate', 'at': '2026-01-06T12:00:00Z',
     'ingested_at': '2026-01-06T12:00:00Z'},
]
SEGMAP = {'u1': 'organic', 'u2': 'paid'}
ASOF = '2026-01-20T00:00:00Z'
BANNED = ['causes', 'caused by', 'causal effect', 'proves', 'will increase',
          'will improve', 'proving']


class DashboardTests(unittest.TestCase):
    def test_cutoff_and_definition_shown(self):
        page = build_dashboard(FIXTURE, SEGMAP, ASOF)
        self.assertIn('2026-01-20T00:00:00', page)
        self.assertIn('signup+7d', page)
        self.assertIn('signup+14d', page)

    def test_numerators_and_denominators_shown(self):
        page = build_dashboard(FIXTURE, SEGMAP, ASOF)
        # Every cohort row shows both ratios explicitly.
        self.assertIn('1/1 = 1.000', page)
        self.assertIn('0/1 = 0.000', page)

    def test_rows_trace_to_source(self):
        page = build_dashboard(FIXTURE, SEGMAP, ASOF)
        table = segment_cohorts(FIXTURE, ASOF, SEGMAP)['cohorts']
        for (monday, segment) in table:
            self.assertIn('data-cohort="%s"' % monday, page)
            self.assertIn('data-segment="%s"' % segment, page)
        self.assertIn('data-source=', page)
        self.assertIn('segments.py', page)

    def test_unknown_row_present(self):
        page = build_dashboard(FIXTURE, SEGMAP, ASOF)
        self.assertIn('data-segment="unknown"', page)

    def test_incomplete_window_is_na_not_zero(self):
        young = [{'id': '1', 'user': 'u1', 'type': 'signup',
                  'at': '2026-01-18T10:00:00Z',
                  'ingested_at': '2026-01-18T10:00:00Z'}]
        page = build_dashboard(young, {'u1': 'organic'}, ASOF)
        self.assertIn('n/a (incomplete window)', page)

    def test_disclaimer_is_descriptive_only(self):
        page = build_dashboard(FIXTURE, SEGMAP, ASOF).lower()
        self.assertIn('descriptive', page)
        self.assertIn('not evidence', page)
        self.assertIn('observed associations', page)
        for phrase in BANNED:
            self.assertNotIn(phrase, page)

    def test_memo_matches_recomputed_table_and_refuses_causality(self):
        memo = Path(__file__).with_name('DECISION_MEMO.md').read_text(
            encoding='utf-8')
        table = segment_cohorts(FIXTURE, ASOF, SEGMAP)['cohorts']
        # Memo denominators match the recomputed source table.
        self.assertIn('2026-01-20T00:00:00Z', memo)
        self.assertIn('1/1 = 1.000', memo)
        self.assertIn('0/1 = 0.000', memo)
        self.assertIn(str(table[('2026-01-05', 'organic')]
                            ['week1_retained']), memo)
        lowered = memo.lower()
        self.assertIn('descriptive', lowered)
        self.assertIn('not causal', lowered.replace('non-causal', 'not causal')
                      if 'non-causal' in lowered else lowered)
        for phrase in BANNED:
            self.assertNotIn(phrase, lowered)
        # Memo records its limits instead of claiming a launch win.
        self.assertIn('Limitations', memo)
        self.assertIn('Do not ship', memo)


if __name__ == '__main__':
    unittest.main()
