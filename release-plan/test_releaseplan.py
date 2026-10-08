"""P16-01: the approved baseline stays distinguishable from later scope changes."""
import copy
import json
import unittest
from pathlib import Path

import releaseplan as rp
from releaseplan import CharterError

CHARTER = Path(__file__).resolve().parent / 'charter.json'


def _charter_tasks():
    charter = _load()
    for task in charter['baseline']['tasks']:
        yield task
    for change in charter['changes']:
        for task in change.get('adds_tasks', []):
            yield task


def _charter_gates():
    charter = _load()
    for gate in charter['baseline']['gates']:
        yield gate
    for change in charter['changes']:
        for gate in change.get('adds_gates', []):
            yield gate



def _load():
    return rp.load_charter(CHARTER)


class CharterValidationTests(unittest.TestCase):
    def setUp(self):
        self.charter = _load()

    def test_real_charter_validates(self):
        self.assertTrue(rp.validate_charter(self.charter))

    def test_release_is_declared_solo_without_a_cross_functional_team(self):
        release = self.charter['release']
        self.assertTrue(release['solo'])
        self.assertEqual(release['team_size'], 1)
        self.assertFalse(release['cross_functional_team'])
        self.assertFalse(release['agent_assistance']['is_a_collaborator'])
        self.assertEqual(release['owner']['email'], 'manuvashisth963@gmail.com')

    def test_baseline_must_be_frozen(self):
        broken = copy.deepcopy(self.charter)
        broken['baseline']['frozen'] = False
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_duplicate_task_id_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['baseline']['tasks'].append(
            copy.deepcopy(broken['baseline']['tasks'][0]))
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_task_outside_approved_scope_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['baseline']['tasks'][0]['project'] = 'shift-bench'
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_unlabelled_estimate_rejected(self):
        """Hours without an hours_basis is an unlabeled guess."""
        broken = copy.deepcopy(self.charter)
        del broken['baseline']['tasks'][0]['hours_basis']
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_change_may_not_edit_the_baseline(self):
        broken = copy.deepcopy(self.charter)
        broken['changes'][0]['baseline_modified'] = True
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_change_needs_date_reason_and_source(self):
        for field in ('date', 'reason', 'source', 'type', 'title'):
            broken = copy.deepcopy(self.charter)
            del broken['changes'][0][field]
            with self.assertRaises(CharterError):
                rp.validate_charter(broken)

    def test_thin_reason_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['changes'][0]['reason'] = 'scope grew'
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_unknown_change_type_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['changes'][0]['type'] = 'vibes'
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_change_removing_unknown_task_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['changes'][0]['removes_tasks'] = ['not-a-task']
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_malformed_evidence_rejected(self):
        broken = copy.deepcopy(self.charter)
        broken['baseline']['tasks'][0]['evidence'] = [{'kind': 'document'}]
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)
        broken['baseline']['tasks'][0]['evidence'] = [
            {'path': 'x.txt', 'kind': 'exit-status', 'expect': 0}]
        with self.assertRaises(CharterError):
            rp.validate_charter(broken)

    def test_synthetic_cycle_rejected(self):
        """A cycle introduced by a rewire is caught, not silently planned."""
        broken = copy.deepcopy(self.charter)
        broken['changes'].append({
            'id': 'CHG-BAD', 'date': '2026-10-08', 'type': 'process_change',
            'title': 'cycle', 'reason': 'deliberately invalid test fixture',
            'source': {'document': 'test_releaseplan.py'},
            'rewires': [{'task': 'p04-01', 'depends': ['p04-04']}]})
        rp.validate_charter(broken)
        with self.assertRaises(CharterError):
            rp.apply_changes(broken)


class BaselineVersusChangesTests(unittest.TestCase):
    def setUp(self):
        self.charter = _load()
        self.before = copy.deepcopy(self.charter['baseline'])

    def test_apply_changes_never_mutates_the_baseline_block(self):
        rp.apply_changes(self.charter)
        rp.apply_changes(self.charter, through='CHG-002')
        rp.plan_effective(self.charter)
        self.assertEqual(self.charter['baseline'], self.before)

    def test_baseline_caller_cannot_mutate_the_charter(self):
        view = rp.baseline(self.charter)
        view['tasks'].append({'id': 'intruder'})
        view['status'] = 'REWRITTEN'
        self.assertEqual(self.charter['baseline'], self.before)

    def test_stop_gates_are_in_the_baseline_and_gone_after_chg_001(self):
        base_ids = {t['id'] for t in self.charter['baseline']['tasks']}
        self.assertIn('stop-p04', base_ids)
        self.assertIn('stop-p06', base_ids)
        after = rp.apply_changes(self.charter, through='CHG-001')
        after_ids = {t['id'] for t in after['tasks']}
        self.assertNotIn('stop-p04', after_ids)
        self.assertNotIn('stop-p06', after_ids)
        depends = {t['id']: t['depends'] for t in after['tasks']}
        self.assertEqual(depends['p06-01'], ['p04-04'])
        self.assertEqual(depends['p05-01'], ['p06-04'])

    def test_baseline_scope_is_the_trio_only(self):
        projects = {t['project'] for t in self.charter['baseline']['tasks']
                    if t.get('project')}
        self.assertEqual(projects, {'flow-ledger', 'data-bridge',
                                    'evidence-rag'})
        self.assertEqual(
            sorted(self.charter['baseline']['scope']['included_projects']),
            sorted(['flow-ledger', 'evidence-rag', 'data-bridge']))

    def test_quartet_only_exists_as_a_recorded_change(self):
        diff = rp.scope_diff(self.charter)
        added_projects = set(diff['projects_only_in_effective'])
        self.assertTrue({'experiment-lab', 'cohort-lens',
                         'shift-bench', 'cura-loop'} <= added_projects)
        self.assertEqual(diff['tasks_only_in_baseline'],
                         ['stop-p04', 'stop-p06'])
        self.assertIn('p10-04', diff['tasks_only_in_effective'])
        for task_id in diff['tasks_only_in_effective']:
            self.assertNotEqual(diff['task_provenance'][task_id], 'baseline')

    def test_every_effective_task_carries_provenance(self):
        effective = rp.apply_changes(self.charter)
        for task in effective['tasks']:
            self.assertIn(task['added_by'],
                          {'baseline', 'CHG-001', 'CHG-002', 'CHG-003',
                           'CHG-004', 'CHG-005', 'CHG-006'})
        self.assertEqual(effective['baseline_task_count'], 18)
        self.assertEqual(len(effective['tasks']), 36)

    def test_through_replays_an_intermediate_point(self):
        after_002 = rp.apply_changes(self.charter, through='CHG-002')
        ids = {t['id'] for t in after_002['tasks']}
        self.assertIn('p10-04', ids)
        self.assertNotIn('appledouble-cleanup', ids)
        self.assertNotIn('preflight-doc-freshness', ids)
        self.assertEqual(after_002['applied_changes'], ['CHG-001', 'CHG-002'])

    def test_change_reasons_name_real_sources(self):
        for change in self.charter['changes']:
            self.assertTrue(change['source']['document'])
            self.assertGreaterEqual(len(change['reason']), 20)
        by_id = {c['id']: c for c in self.charter['changes']}
        self.assertIn('2026-10-05', by_id['CHG-001']['date'])
        self.assertEqual(by_id['CHG-003']['source']['commit'], '3be4111')
        self.assertEqual(by_id['CHG-004']['source']['commit'], '5f5e077')
        self.assertEqual(by_id['CHG-005']['type'], 'scope_cut')


class PlanIntegrationTests(unittest.TestCase):
    """The reference plan() from project.py is reused unmodified."""

    def setUp(self):
        self.charter = _load()

    def test_baseline_critical_path_and_estimate(self):
        result = rp.plan_baseline(self.charter)
        self.assertEqual(result['source'], 'baseline')
        self.assertEqual(result['critical_path'], [
            'p04-01', 'p04-02', 'p04-03', 'p04-04', 'stop-p04',
            'p06-01', 'p06-02', 'p06-03', 'p06-04', 'stop-p06',
            'p05-01', 'p05-02', 'p05-03', 'p05-04', 'bundle-p05'])
        self.assertEqual(result['estimated_hours'], 173.0)

    def test_baseline_estimate_inside_the_documented_range(self):
        estimate = self.charter['baseline']['effort_estimate']
        low, high = estimate['documented_range_hours']
        hours = rp.plan_baseline(self.charter)['estimated_hours']
        self.assertTrue(low <= hours <= high, (low, hours, high))

    def test_effective_estimate_grew_and_stays_inside_documented_ranges(self):
        report = rp.estimate_within_documented_range(self.charter)
        self.assertTrue(report['within'])
        self.assertGreater(report['effective_estimated_hours'],
                           report['baseline_estimated_hours'])
        self.assertEqual(report['low'], 290)
        self.assertEqual(report['high'], 460)

    def test_reference_note_is_preserved_not_rewritten(self):
        result = rp.plan_effective(self.charter)
        self.assertIn('estimates are not measured delivery', result['note'])
        self.assertIn('declared, not content-verified', result['note'])

    def test_baseline_plan_is_honestly_not_ready(self):
        """The two stop gates produced no artifact, so the baseline never readied."""
        result = rp.plan_baseline(self.charter)
        self.assertFalse(result['ready_all'])
        self.assertIn('stop-p04', result['not_ready'])
        self.assertIn('stop-p06', result['not_ready'])
        self.assertTrue(result['ready']['p04-04'])
        self.assertTrue(result['ready']['bundle-p04'])
        self.assertFalse(result['ready']['p05-01'])

    def test_effective_plan_is_not_ready_because_review_is_a_human_gate(self):
        result = rp.plan_effective(self.charter)
        self.assertEqual(result['not_ready'],
                         ['gate-user-review-p07-p10', 'gate-user-review-trio1'])
        self.assertFalse(result['ready_all'])

    def test_milestone_status_must_match_its_commit_evidence(self):
        milestones = rp.milestones_with_actuals(self.charter)
        achieved = [m['id'] for m in milestones if m['status'] == 'ACHIEVED']
        self.assertEqual(achieved, ['M0-baseline-approved',
                                    'M1-p04-cards-complete',
                                    'M2-p06-cards-complete',
                                    'M3-p05-cards-complete',
                                    'M4-review-bundles-delivered'])
        broken = copy.deepcopy(self.charter)
        broken['baseline']['milestones'][0]['actual_commit'] = None
        with self.assertRaises(CharterError):
            rp.milestones_with_actuals(broken)
        broken = copy.deepcopy(self.charter)
        broken['baseline']['milestones'][-1]['actual_commit'] = 'deadbeef'
        with self.assertRaises(CharterError):
            rp.milestones_with_actuals(broken)


class ReadinessIsNeverHandCheckedTests(unittest.TestCase):
    def setUp(self):
        self.charter = _load()

    def _every_task(self):
        for task in self.charter['baseline']['tasks']:
            yield task
        for change in self.charter['changes']:
            for task in change.get('adds_tasks', []):
                yield task

    def test_no_task_declares_a_done_boolean(self):
        for task in self._every_task():
            self.assertNotIn('done', task, task['id'])
            self.assertNotIn('ready', task, task['id'])

    def test_done_is_derived_by_the_resolver(self):
        planned = rp.tasks_for_plan(self.charter['baseline']['tasks'])
        by_id = {t['id']: t for t in planned}
        self.assertTrue(by_id['p04-01']['done'])
        self.assertFalse(by_id['stop-p04']['done'])
        self.assertEqual(by_id['stop-p04']['evidence'], [])

    def test_declared_resolve_trusts_only_the_transcribed_exit(self):
        ok, paths, source = rp.declared_resolve(
            {'path': 'a.txt', 'kind': 'exit-status', 'exit_key': None,
             'expect': 0, 'recorded_exit': 0})
        self.assertTrue(ok)
        self.assertEqual(source, 'declared')
        ok, _, _ = rp.declared_resolve(
            {'path': 'a.txt', 'kind': 'exit-status', 'exit_key': None,
             'expect': 0, 'recorded_exit': 1})
        self.assertFalse(ok)

    def test_empty_evidence_is_never_ready(self):
        result = rp.resolve_task({'id': 'x', 'evidence': []},
                                 rp.declared_resolve)
        self.assertFalse(result['ok'])
        self.assertEqual(result['source'], 'none')
        self.assertTrue(result['reason'])

    def test_one_failed_artifact_fails_the_whole_task(self):
        task = {'id': 'x', 'evidence': [
            {'path': 'good.txt', 'kind': 'document'},
            {'path': 'bad.txt', 'kind': 'exit-status', 'exit_key': None,
             'expect': 0, 'recorded_exit': 2}]}
        self.assertFalse(rp.resolve_task(task, rp.declared_resolve)['ok'])


class CharterFileIntegrityTests(unittest.TestCase):
    def test_charter_on_disk_is_valid_json_and_round_trips(self):
        raw = json.loads(CHARTER.read_text(encoding='utf-8'))
        self.assertEqual(raw['schema_version'], 1)
        self.assertEqual(raw['release']['id'], 'R1-trio1-review')
        self.assertEqual(len(raw['changes']), 6)

    def test_every_declared_artifact_path_is_relative_and_clean(self):
        seen = set()

        def walk(specs):
            for spec in specs:
                self.assertFalse(spec['path'].startswith('/'), spec['path'])
                self.assertNotIn('..', spec['path'].split('/'), spec['path'])
                seen.add(spec['path'])

        for task in _charter_tasks():
            walk(task['evidence'])
        for gate in _charter_gates():
            walk(gate['artifacts'])
        self.assertGreater(len(seen), 40)


if __name__ == '__main__':
    unittest.main()
