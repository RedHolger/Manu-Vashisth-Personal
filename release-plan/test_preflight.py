"""P16-04b: the preflight checker detects real drift and can also pass.

No git write command is used anywhere in this file. The synthetic-repository
cases stub preflight's git layer with canned output, so the checker is proven
capable of returning OK / exit 0 without ever creating a repository. The
real-repository cases run the actual read-only git plumbing.
"""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import preflight
from fakegit import (clean_repo, patched_run, set_committed,
                     set_working)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


class WithheldParsingTests(unittest.TestCase):
    def test_en_dash_range(self):
        text = '- Not authorized and still withheld: starting P07\u2013P22.'
        self.assertEqual(preflight.withheld_project_numbers(text),
                         list(range(7, 23)))

    def test_hyphen_range_and_single_ids(self):
        text = 'Not authorized and still withheld: P11-P13 and P20.'
        self.assertEqual(preflight.withheld_project_numbers(text),
                         [11, 12, 13, 20])

    def test_no_withholding_clause(self):
        self.assertEqual(preflight.withheld_project_numbers('# Plan\n'), [])

    def test_unrelated_lines_are_ignored(self):
        text = ('- Authorized: P04 through P06.\n'
                'Some other line mentioning P09 in passing.\n')
        self.assertEqual(preflight.withheld_project_numbers(text), [])


class SyntheticRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='p16-preflight-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_a_clean_repository_passes_with_exit_zero(self):
        report = patched_run(clean_repo(self.tmp))
        self.assertEqual(report['exit_code'], 0)
        self.assertEqual(report['counts']['FAIL'], 0)
        self.assertTrue(all(f['severity'] != preflight.SEVERITY_FAIL
                            for f in report['findings']))
        self.assertEqual(len(report['findings']), 5)

    def test_authorization_drift_is_detected(self):
        repo = clean_repo(self.tmp)
        set_committed(repo, 'PLAN.md',
                       '# Plan\n\n- Not authorized and still withheld: '
                       'starting P88\u2013P95.\n')
        report = patched_run(repo)
        pf1 = next(f for f in report['findings'] if f['id'] == 'PF-1')
        self.assertEqual(pf1['severity'], preflight.SEVERITY_FAIL)
        self.assertEqual(pf1['evidence']['delivered_but_withheld_at_HEAD'],
                         ['P90-demo'])
        self.assertEqual(report['exit_code'], 1)

    def test_uncommitted_authorization_is_a_warning(self):
        repo = clean_repo(self.tmp)
        set_working(repo, 'PLAN.md', repo.committed_files['PLAN.md'] +
                     '\n2026-10-06 scope update: continue through P04-P22.\n')
        report = patched_run(repo)
        pf1 = next(f for f in report['findings'] if f['id'] == 'PF-1')
        self.assertEqual(pf1['severity'], preflight.SEVERITY_WARN)
        self.assertTrue(pf1['evidence']['plan_working_tree_differs_from_HEAD'])

    def test_missing_committed_plan_is_a_failure(self):
        repo = clean_repo(self.tmp)
        del repo.committed_files['PLAN.md']
        report = patched_run(repo)
        pf1 = next(f for f in report['findings'] if f['id'] == 'PF-1')
        self.assertEqual(pf1['severity'], preflight.SEVERITY_FAIL)
        self.assertIn('no committed PLAN.md', pf1['summary'])

    def test_a_status_doc_that_lags_its_own_projects_is_stale(self):
        repo = clean_repo(self.tmp)
        set_committed(repo, 'PORTFOLIO_STATUS.md', '# Status\n\nP04 only.\n')
        repo.commits_since[('bbbbbbb', 'P90-demo')] = 4
        report = patched_run(repo)
        pf2 = next(f for f in report['findings'] if f['id'] == 'PF-2')
        self.assertEqual(pf2['severity'], preflight.SEVERITY_FAIL)
        detail = pf2['evidence']['PORTFOLIO_STATUS.md']
        self.assertEqual(detail['delivered_projects_not_mentioned'],
                         ['P90-demo'])
        self.assertEqual(detail['projects_with_commits_after_doc'],
                         [{'project': 'P90-demo', 'commits_after_doc': 4}])
        self.assertEqual(detail['commits_since_doc'], 0)

    def test_a_mentioned_and_current_doc_is_not_stale(self):
        report = patched_run(clean_repo(self.tmp))
        pf2 = next(f for f in report['findings'] if f['id'] == 'PF-2')
        self.assertEqual(pf2['severity'], preflight.SEVERITY_OK)
        self.assertEqual(pf2['evidence']['PORTFOLIO_STATUS.md']
                         ['delivered_projects_not_mentioned'], [])

    def test_tracked_build_artifacts_are_a_failure(self):
        repo = clean_repo(self.tmp)
        repo.tracked += ['P90-demo/target/classes/App.class',
                         'P90-demo/target/surefire-reports/TEST.xml']
        report = patched_run(repo)
        pf3 = next(f for f in report['findings'] if f['id'] == 'PF-3')
        self.assertEqual(pf3['severity'], preflight.SEVERITY_FAIL)
        self.assertEqual(pf3['evidence']['count'], 2)
        self.assertEqual(pf3['evidence']['by_top_level_dir'], {'P90-demo': 2})

    def test_untracked_sidecars_warn_and_tracked_ones_fail(self):
        repo = clean_repo(self.tmp)
        repo.status = ['?? ._PLAN.md', '?? P90-demo/._project.py']
        report = patched_run(repo)
        pf4 = next(f for f in report['findings'] if f['id'] == 'PF-4')
        self.assertEqual(pf4['severity'], preflight.SEVERITY_WARN)
        self.assertEqual(pf4['evidence']['in_status'], 2)
        self.assertEqual(pf4['evidence']['tracked'], 0)

        repo.tracked.append('P90-demo/._project.py')
        report = patched_run(repo)
        pf4 = next(f for f in report['findings'] if f['id'] == 'PF-4')
        self.assertEqual(pf4['severity'], preflight.SEVERITY_FAIL)
        self.assertEqual(pf4['evidence']['tracked'], 1)

    def test_staged_sidecars_fail(self):
        repo = clean_repo(self.tmp)
        repo.status = ['A  P90-demo/._project.py']
        report = patched_run(repo)
        pf4 = next(f for f in report['findings'] if f['id'] == 'PF-4')
        self.assertEqual(pf4['severity'], preflight.SEVERITY_FAIL)
        self.assertEqual(pf4['evidence']['staged'], 1)

    def test_results_dir_without_a_command_is_a_warning(self):
        repo = clean_repo(self.tmp)
        run_dir = repo.root / 'P90-demo' / 'results' / 'p90-01-slice'
        run_dir.mkdir(parents=True)
        report = patched_run(repo)
        pf5 = next(f for f in report['findings'] if f['id'] == 'PF-5')
        self.assertEqual(pf5['severity'], preflight.SEVERITY_WARN)
        self.assertEqual(pf5['evidence']['missing_command_txt'],
                         ['P90-demo/p90-01-slice'])
        (run_dir / 'command.txt').write_text('python3 -B test.py\n',
                                             encoding='utf-8')
        report = patched_run(repo)
        pf5 = next(f for f in report['findings'] if f['id'] == 'PF-5')
        self.assertEqual(pf5['severity'], preflight.SEVERITY_OK)

    def test_a_non_repository_is_refused(self):
        empty = Path(tempfile.mkdtemp(prefix='p16-norepo-'))
        self.addCleanup(shutil.rmtree, empty, True)
        with self.assertRaises(preflight.PreflightError):
            preflight.run(empty)


class RealRepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.report = preflight.run(REPO_ROOT)
        cls.by_id = {f['id']: f for f in cls.report['findings']}

    def test_the_real_demonstrated_failures_are_detected(self):
        self.assertEqual(self.by_id['PF-1']['severity'],
                         preflight.SEVERITY_FAIL)
        # Recalibrated 2026-10-08 (was P07-P10 only): P11-P22 are delivered
        # (committed) but acceptance is withheld (nothing is ACCEPTED), so
        # the detector correctly still flags them. Working tree differs
        # (uncommitted handoff working files + trio leftovers).
        self.assertEqual(
            self.by_id['PF-1']['evidence']['delivered_but_withheld_at_HEAD'],
            ['experiment-lab', 'cohort-lens', 'shift-bench',
             'cura-loop', 'access-guard', 'incident-replay',
             'ops-console', 'study-path', 'user-evidence',
             'release-plan', 'launch-lab', 'fleet-doctor',
             'packet-lab', 'edge-bench', 'silicon-check',
             'enclosure-lab'])
        self.assertTrue(
            self.by_id['PF-1']['evidence']
            ['plan_working_tree_differs_from_HEAD'])

    def test_both_root_status_docs_are_fresh(self):
        # Maintained (Codex): docs are fresh when they mention every delivered
        # project. Asserts only the timeless content property
        # (nothing unmentioned) — commit counts and lag are transient and
        # belong to the detector's evidence, not the gate. Catches real
        # staleness (delivered-but-unmentioned projects).
        pf2 = self.by_id['PF-2']
        self.assertEqual(pf2['severity'], preflight.SEVERITY_OK)
        for doc in ('PORTFOLIO_STATUS.md', 'HANDOFF.md'):
            detail = pf2['evidence'][doc]
            self.assertEqual(detail['delivered_projects_not_mentioned'], [])

    def test_tracked_build_artifacts_are_counted(self):
        pf3 = self.by_id['PF-3']
        self.assertEqual(pf3['severity'], preflight.SEVERITY_FAIL)
        self.assertEqual(pf3['evidence']['count'], 54)
        self.assertEqual(pf3['evidence']['by_top_level_dir'],
                         {'flow-ledger': 54})

    def test_sidecars_are_untracked_noise_not_a_commit_risk_right_now(self):
        # Maintained (Codex): the repo .gitignore now covers `._*`, so ExFAT
        # sidecars no longer pollute `git status` — the detector correctly
        # reports OK (was WARN at 500+ listed). Asserts the healthy state and
        # its cause (the ignore rule), not a fixed count.
        pf4 = self.by_id['PF-4']
        self.assertEqual(pf4['severity'], preflight.SEVERITY_OK)
        self.assertEqual(pf4['evidence']['tracked'], 0)
        self.assertEqual(pf4['evidence']['staged'], 0)
        from pathlib import Path
        self.assertIn('._*', (REPO_ROOT / '.gitignore').read_text())

    def test_the_report_says_it_is_read_only_and_exits_nonzero(self):
        self.assertTrue(self.report['read_only'])
        self.assertEqual(self.report['exit_code'], 1)
        # Maintained (Codex): PF-2 remediated (OK) and PF-4 quieted by
        # .gitignore (OK); PF-1 (withheld) + PF-3 (artifacts) still FAIL,
        # PF-5 still WARNs. Exit stays nonzero by design.
        self.assertEqual(self.report['counts']['FAIL'], 2)
        self.assertEqual(self.report['counts']['WARN'], 1)
        self.assertEqual(self.report['counts']['OK'], 2)
        self.assertEqual(self.report['git_head'], subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True).stdout.strip())

    def test_every_out_of_scope_fix_is_a_recommendation_not_an_edit(self):
        for item in self.report['findings']:
            self.assertEqual(item['owner_scope'], 'outside-p16')
            if item['severity'] != preflight.SEVERITY_OK:
                self.assertTrue(item['recommendation'])
                self.assertNotEqual(item['recommendation'], 'none')

    def test_running_the_checker_changes_nothing(self):
        docs = ['PLAN.md', 'PORTFOLIO_STATUS.md', 'HANDOFF.md',
                'TRIO1_P04-P06_PLAN.md']

        def digest():
            return {d: hashlib.sha256((REPO_ROOT / d).read_bytes()).hexdigest()
                    for d in docs}

        def status():
            return subprocess.run(
                ['git', '-C', str(REPO_ROOT), 'status', '--porcelain'],
                capture_output=True, text=True).stdout

        before_docs, before_status = digest(), status()
        preflight.run(REPO_ROOT)
        self.assertEqual(digest(), before_docs)
        self.assertEqual(status(), before_status)

    def test_render_lists_every_finding(self):
        text = preflight.render(self.report)
        for item in self.report['findings']:
            self.assertIn(item['id'], text)
            self.assertIn(item['severity'], text)
        self.assertIn('exit_code: 1', text)


if __name__ == '__main__':
    unittest.main()
