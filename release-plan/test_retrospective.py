"""P16-04a: the retrospective reads real git history and explains every gap."""
import json
import subprocess
import unittest
from pathlib import Path

import releaseplan as rp
import retrospective as rt

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
CHARTER = HERE / 'charter.json'


def _rev_count():
    return int(subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'rev-list', '--count', 'HEAD'],
        capture_output=True, text=True).stdout.strip())


class CommitParsingTests(unittest.TestCase):
    def test_card_ranges_expand(self):
        commit = {'subject': 'P10-02..04 curateloop: versioned store, fair AL '
                             'comparison, consent-gated human timing'}
        self.assertEqual(rt.cards_in(commit), ['P10-02', 'P10-03', 'P10-04'])

    def test_single_card(self):
        self.assertEqual(
            rt.cards_in({'subject': 'P04-01 reference reconciliation: gap '
                                    'table'}), ['P04-01'])

    def test_project_mentions_without_cards_are_not_cards(self):
        for subject in ('P01-P03 audits: SRE repos located and mapped',
                        'P04 v1 complete: concurrent-conflict, atomicity',
                        'P04 FlowLedger v1: durable execution',
                        'Review bundles: implementation-inclusive P04/P06/P05 '
                        'ZIPs with hash manifests',
                        'Remove AppleDouble sidecars accidentally staged with '
                        'the P07 kit directory',
                        'Add Trio 1 portfolio maintenance records'):
            self.assertEqual(rt.cards_in({'subject': subject}), [], subject)


class RealGitHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.charter = rp.load_charter(CHARTER)
        cls.commits = rt.commits(REPO_ROOT)
        cls.report = rt.report(cls.charter, REPO_ROOT)

    def test_commit_count_matches_git_rev_list(self):
        self.assertEqual(len(self.commits), _rev_count())
        self.assertEqual(self.report['total_commits'], _rev_count())

    def test_every_commit_record_is_utc_and_ordered(self):
        for commit in self.commits:
            self.assertTrue(commit['date_utc'].endswith('Z'), commit)
            self.assertEqual(len(commit['sha']), 40)
        epochs = [c['epoch'] for c in self.commits]
        self.assertEqual(epochs, sorted(epochs, reverse=True))

    def test_solo_history_is_reported_as_solo(self):
        self.assertTrue(self.report['solo'])
        self.assertEqual(self.report['distinct_author_identities'],
                         ['RedHolger <manuvashisth963@gmail.com>',
                          'manu <manu@local>'])
        self.assertGreaterEqual(self.report['agent_assisted_commits'], 20)

    def test_every_card_has_a_real_commit(self):
        index = rt.card_index(REPO_ROOT)
        # Recalibrated 2026-10-08 (was 28 = 7x4): 30 cards index by subject
        # (P04-P10 plus P12-03/P12-04, whose subjects name them). P11/P13-P22
        # subjects say "all 4 cards" without naming them, so those cards are
        # covered by project_delivery below, not by this index. Future
        # commits should name cards (recorded as a refinement).
        self.assertEqual(len(index), 30)
        for card, commit in index.items():
            self.assertTrue(commit['sha'])
            self.assertIn(card, rt.cards_in(commit))

    def test_head_matches_git(self):
        expected = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True).stdout.strip()
        self.assertEqual(self.report['git_head'], expected)

    def test_undelivered_directory_reports_as_undelivered(self):
        # Recalibrated 2026-10-08 (P16 was undelivered with 0 commits; it has
        # since been committed): P16 now reports delivered, and every P11-P22
        # project directory likewise shows real commits (covering the cards
        # whose subjects do not name them — see card_index note above).
        actual = rt.project_delivery(REPO_ROOT, 'release-plan')
        self.assertGreater(actual['commits'], 0)
        self.assertTrue(actual['delivered'])
        self.assertIsNotNone(actual['first_commit'])
        for project in ('access-guard', 'ops-console', 'study-path',
                        'user-evidence', 'launch-lab', 'fleet-doctor',
                        'packet-lab', 'edge-bench', 'silicon-check',
                        'enclosure-lab'):
            delivery = rt.project_delivery(REPO_ROOT, project)
            self.assertTrue(delivery['delivered'], project)
            self.assertGreater(delivery['commits'], 0, project)


class PlannedVersusActualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.charter = rp.load_charter(CHARTER)
        cls.report = rt.report(cls.charter, REPO_ROOT)
        cls.rows = {r['project']: r for r in cls.report['rows']}

    def test_every_charter_project_has_a_planned_range_and_an_actual_row(self):
        ranges = rt.planned_ranges(self.charter)
        self.assertEqual(sorted(ranges), ['flow-ledger', 'evidence-rag',
                                          'data-bridge', 'experiment-lab',
                                          'cohort-lens', 'shift-bench',
                                          'cura-loop'])
        for project, low_high in ranges.items():
            self.assertEqual(len(low_high), 2)
            self.assertLess(low_high[0], low_high[1])
            self.assertIn(project, self.rows)
            self.assertEqual(self.rows[project]['planned_hours_range'],
                             low_high)

    def test_wall_clock_span_is_never_presented_as_effort(self):
        for row in self.report['rows']:
            self.assertFalse(row['effort_measurable'])
            self.assertIn('actual_span_hours_wall_clock', row)
            self.assertNotIn('actual_hours', row)
        text = json.dumps(self.report)
        for forbidden in ('actual_hours', 'measured_effort', 'hours_spent',
                          'velocity', 'productivity_gain'):
            self.assertNotIn(forbidden, text)
        self.assertIn('NOT measured effort', self.report['effort_disclaimer'])
        self.assertIn('no timesheet exists', self.report['effort_disclaimer'])

    def test_actual_commit_counts_are_read_from_git_not_typed(self):
        for project in ('flow-ledger', 'evidence-rag', 'data-bridge',
                        'experiment-lab', 'cohort-lens',
                        'shift-bench', 'cura-loop'):
            expected = int(subprocess.run(
                ['git', '-C', str(REPO_ROOT), 'rev-list', '--count', 'HEAD',
                 '--', project], capture_output=True, text=True).stdout)
            self.assertEqual(self.rows[project]['actual_commits'], expected,
                             project)
        self.assertEqual(self.rows['cura-loop']['actual_commits'], 2)
        self.assertEqual(self.rows['flow-ledger']['actual_commits'], 7)

    def test_planned_order_was_actually_kept(self):
        order = self.report['order']
        self.assertTrue(order['order_matched'])
        self.assertEqual(order['planned_order'][:3],
                         ['flow-ledger', 'data-bridge',
                          'evidence-rag'])
        self.assertEqual(order['release_projects_in_actual_order'][:3],
                         order['planned_order'][:3])
        self.assertEqual(order['release_projects_in_actual_order'],
                         ['flow-ledger', 'data-bridge',
                          'evidence-rag', 'experiment-lab',
                          'cohort-lens', 'shift-bench',
                          'cura-loop'])


class DeviationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.charter = rp.load_charter(CHARTER)
        cls.deviations = {d['id']: d
                          for d in rt.report(cls.charter, REPO_ROOT)[
                              'deviations']}

    def test_a_deviation_without_an_explanation_is_refused(self):
        with self.assertRaises(rt.RetroError):
            rt.deviation('X', 'scope', 1, 2, 'grew', {'document': 'PLAN.md'})
        with self.assertRaises(rt.RetroError):
            rt.deviation('X', 'scope', 1, 2,
                         'a sufficiently long explanation of the deviation',
                         {})

    def test_every_deviation_is_explained_and_sourced(self):
        self.assertEqual(len(self.deviations), 8)
        for entry in self.deviations.values():
            self.assertGreaterEqual(len(entry['explanation']), 40)
            self.assertTrue(entry['source']['document'])
            self.assertIn(entry['severity'], ('none', 'minor', 'material'))

    def test_the_calendar_deviation_is_real_and_labelled(self):
        dev = self.deviations['DEV-1']
        self.assertEqual(dev['kind'], 'calendar')
        self.assertIn('12-27 weeks', dev['planned'])
        self.assertIn('days of wall-clock span', dev['actual'])
        self.assertIn('not focused hours', dev['explanation'])

    def test_implementation_before_approval_is_reported(self):
        dev = self.deviations['DEV-4']
        self.assertEqual(dev['source']['commit'], 'b1e974f')
        self.assertIn('plan review only. No implementation.', dev['planned'])
        self.assertIn('106 lines', dev['actual'])

    def test_multi_card_commit_is_reported(self):
        dev = self.deviations['DEV-5']
        self.assertIn('a7a1a83', dev['actual'])
        self.assertEqual(sorted(dev['actual']['a7a1a83']),
                         ['P10-02', 'P10-03', 'P10-04'])

    def test_unplanned_corrective_commit_is_reported(self):
        dev = self.deviations['DEV-6']
        self.assertEqual(dev['source']['commit'], '3be4111')
        self.assertIn('narrower than the risk', dev['explanation'])

    def test_missing_acceptance_is_reported_not_glossed(self):
        dev = self.deviations['DEV-7']
        # Recalibrated 2026-10-08 (was "0 of 7"): charter scope now counts 8
        # delivered projects; still zero ACCEPTED (true — nothing is).
        self.assertIn('0 of 8 delivered projects are ACCEPTED', dev['actual'])
        self.assertIn('5 of 6 baseline milestones achieved', dev['actual'])

    def test_bundle_gap_is_reported(self):
        dev = self.deviations['DEV-8']
        # Recalibrated 2026-10-08 (was "3 ZIPs ... 7 delivered"): 19 real
        # ZIPs (sidecars excluded by the DEV-8 counter fix) for 8 delivered.
        self.assertTrue(dev['actual'].startswith('19 ZIPs exist'))
        self.assertNotIn('._', dev['actual'])
        self.assertTrue(dev['actual'].endswith('8 delivered projects'))


if __name__ == '__main__':
    unittest.main()
