"""P16-02: readiness is measured from artifacts, so it cannot be faked."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import releaseplan as rp
import verify
from verify import ArtifactVerifier

REAL_CHARTER = Path(__file__).resolve().parent / 'charter.json'
REPO_ROOT = Path(__file__).resolve().parent.parent


def _spec(path, kind='exit-status', expect=0, recorded=0, key=None, **extra):
    spec = {'path': path, 'kind': kind, 'expect': expect,
            'recorded_exit': recorded, 'exit_key': key}
    spec.update(extra)
    return spec


def _task(task_id, depends=(), evidence=(), hours=1, owner='RedHolger'):
    return {'id': task_id, 'title': task_id, 'depends': list(depends),
            'hours': hours, 'hours_basis': 'test fixture', 'owner': owner,
            'evidence': list(evidence)}


class TempRepoMixin(unittest.TestCase):
    """A throwaway repository root so no real evidence is ever touched."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='p16-verify-'))
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, relpath, text):
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return relpath

    def verifier(self):
        return ArtifactVerifier(self.root)


class ParseExitStatusTests(unittest.TestCase):
    def test_bare_integer(self):
        self.assertEqual(ArtifactVerifier.parse_exit_status('0\n'),
                         {'exit': 0})
        self.assertEqual(ArtifactVerifier.parse_exit_status('1'),
                         {'exit': 1})

    def test_key_value_lines(self):
        text = 'assertions_passed=40\nassertions_failed=0\nexit=0\n'
        self.assertEqual(ArtifactVerifier.parse_exit_status(text),
                         {'assertions_passed': 40, 'assertions_failed': 0,
                          'exit': 0})

    def test_no_trailing_newline(self):
        self.assertEqual(ArtifactVerifier.parse_exit_status('1'), {'exit': 1})

    def test_empty_and_garbage_rejected(self):
        for text in ('', '   \n', 'ok\n', 'exit=zero\n'):
            with self.assertRaises(ValueError):
                ArtifactVerifier.parse_exit_status(text)


class ArtifactVerificationTests(TempRepoMixin):
    def test_existing_exit_status_zero_verifies(self):
        self.write('results/a/measure-exit-status.txt', '0\n')
        record = self.verifier().verify_artifact(_spec(
            'results/a/measure-exit-status.txt'))
        self.assertTrue(record['ok'])
        self.assertTrue(record['exists'])
        self.assertEqual(record['recorded_status'], {'exit': 0})
        self.assertEqual(len(record['sha256']), 64)
        self.assertEqual(record['role'], 'acceptance-run')
        self.assertTrue(record['required'])

    def test_missing_artifact_fails_with_a_reason(self):
        record = self.verifier().verify_artifact(_spec('results/nope.txt'))
        self.assertFalse(record['ok'])
        self.assertFalse(record['exists'])
        self.assertIn('missing', record['reason'])

    def test_nonzero_exit_status_fails(self):
        self.write('results/a/exit.txt', '1\n')
        record = self.verifier().verify_artifact(_spec('results/a/exit.txt'))
        self.assertFalse(record['ok'])
        self.assertIn('expected 0', record['reason'])

    def test_declared_expectation_is_honoured_for_failed_attempts(self):
        """A retained failing attempt must still record a failure."""
        self.write('results/a/attempt1-exit-status.txt', '1\n')
        ok = self.verifier().verify_artifact(_spec(
            'results/a/attempt1-exit-status.txt', expect=1, recorded=1,
            role='retained-failed-attempt', required=False))
        self.assertTrue(ok['ok'])
        laundered = self.verifier().verify_artifact(_spec(
            'results/a/attempt1-exit-status.txt', expect=0, recorded=0,
            role='retained-failed-attempt', required=False))
        self.assertFalse(laundered['ok'])

    def test_multi_key_file_uses_the_declared_key(self):
        self.write('results/a/exit.txt',
                   'assertions_passed=40\nassertions_failed=0\nexit=0\n')
        with_key = self.verifier().verify_artifact(
            _spec('results/a/exit.txt', key='exit'))
        self.assertTrue(with_key['ok'])
        wrong_key = self.verifier().verify_artifact(
            _spec('results/a/exit.txt', key='assertions_passed'))
        self.assertFalse(wrong_key['ok'])

    def test_multi_key_file_falls_back_to_exit_then_fails_closed(self):
        self.write('results/a/exit.txt', 'failed=0\nexit=0\n')
        self.assertTrue(self.verifier().verify_artifact(
            _spec('results/a/exit.txt'))['ok'])
        self.write('results/b/exit.txt', 'passed=40\nfailed=0\n')
        record = self.verifier().verify_artifact(_spec('results/b/exit.txt'))
        self.assertFalse(record['ok'])
        self.assertIn('ambiguous', record['reason'])

    def test_empty_document_is_not_evidence(self):
        self.write('results/a/README.md', '')
        record = self.verifier().verify_artifact(
            _spec('results/a/README.md', kind='document'))
        self.assertFalse(record['ok'])
        self.assertEqual(record['reason'], 'empty artifact')

    def test_directory_is_not_a_file_artifact(self):
        (self.root / 'results' / 'a').mkdir(parents=True)
        record = self.verifier().verify_artifact(
            _spec('results/a', kind='document'))
        self.assertFalse(record['ok'])
        self.assertIn('directory', record['reason'])

    def test_paths_cannot_escape_the_repository_root(self):
        for bad in ('../PORTFOLIO_STATUS.md', '/etc/passwd',
                    'results/../../secret.txt'):
            record = self.verifier().verify_artifact(_spec(bad))
            self.assertFalse(record['ok'], bad)
            self.assertIn('escapes', record['reason'])
            self.assertFalse(record['exists'])


class TaskAndGateVerificationTests(TempRepoMixin):
    def test_task_with_no_evidence_is_never_ok(self):
        result = self.verifier().verify_task(_task('x', evidence=[]))
        self.assertFalse(result['ok'])
        self.assertEqual(result['required_total'], 0)
        self.assertTrue(result['reason'])

    def test_optional_artifacts_alone_cannot_ready_a_task(self):
        self.write('a.txt', '1\n')
        result = self.verifier().verify_task(_task('x', evidence=[
            _spec('a.txt', expect=1, recorded=1,
                  role='retained-failed-attempt', required=False)]))
        self.assertFalse(result['ok'])
        self.assertIn('no required evidence', result['reason'])

    def test_one_failing_required_artifact_fails_the_task(self):
        self.write('good.txt', '0\n')
        self.write('bad.txt', '1\n')
        result = self.verifier().verify_task(_task('x', evidence=[
            _spec('good.txt'), _spec('bad.txt')]))
        self.assertFalse(result['ok'])
        self.assertEqual(result['required_ok'], 1)
        self.assertEqual(result['required_total'], 2)
        self.assertIn('bad.txt', result['reason'])

    def test_retained_failure_does_not_block_an_otherwise_passing_task(self):
        self.write('measure-exit-status.txt', '0\n')
        self.write('attempt1-exit-status.txt', '1\n')
        result = self.verifier().verify_task(_task('x', evidence=[
            _spec('measure-exit-status.txt'),
            _spec('attempt1-exit-status.txt', expect=1, recorded=1,
                  role='retained-failed-attempt', required=False)]))
        self.assertTrue(result['ok'])
        self.assertEqual(result['artifacts_total'], 2)
        self.assertEqual(result['optional_total'], 1)
        self.assertEqual(result['retained_failures_laundered'], [])

    def test_a_retained_failed_attempt_that_passed_is_flagged(self):
        self.write('measure-exit-status.txt', '0\n')
        self.write('attempt1-exit-status.txt', '0\n')
        result = self.verifier().verify_task(_task('x', evidence=[
            _spec('measure-exit-status.txt'),
            _spec('attempt1-exit-status.txt', expect=0, recorded=0,
                  role='retained-failed-attempt', required=False)]))
        self.assertEqual(result['retained_failures_laundered'],
                         ['attempt1-exit-status.txt'])

    def test_human_decision_gate_is_never_ok_even_with_artifacts(self):
        self.write('signed-acceptance.txt', 'accepted\n')
        gate = {'id': 'G', 'requires_human_decision': True,
                'artifacts': [_spec('signed-acceptance.txt', kind='document')],
                'reason_no_artifact': 'human decision'}
        result = self.verifier().verify_gate(gate)
        self.assertFalse(result['ok'])
        self.assertTrue(result['human_decision_required'])

    def test_gate_with_no_artifact_refuses_vacuous_truth(self):
        result = self.verifier().verify_gate({'id': 'G', 'artifacts': []})
        self.assertFalse(result['ok'])
        self.assertIn('vacuous truth', result['reason'])


class ReadinessCannotBeFakedTests(TempRepoMixin):
    """The acceptance rule: blocked or unverified work cannot appear ready."""

    def _charter(self, evidence_a, evidence_b):
        return {
            'schema_version': 1,
            'release': {'id': 'T', 'solo': True, 'team_size': 1,
                        'cross_functional_team': False,
                        'owner': {'email': 'x'}},
            'baseline': {
                'id': 'B', 'frozen': True, 'status': 'APPROVED',
                'approved_at': '2026-10-08', 'approved_by': 'owner',
                'scope': {'included_projects': []},
                'effort_estimate': {'documented_range_hours': [0, 10],
                                    'source': 'fixture'},
                'milestones': [], 'gates': [],
                'tasks': [_task('a', evidence=evidence_a),
                          _task('b', depends=['a'], evidence=evidence_b)]},
            'changes': []}

    def _ready(self, charter):
        report = self.verifier().verify_charter(charter)
        return report['plan']['ready'], report

    def test_missing_artifact_makes_the_task_not_ready(self):
        self.write('b/measure-exit-status.txt', '0\n')
        ready, report = self._ready(self._charter(
            [_spec('a/measure-exit-status.txt')],
            [_spec('b/measure-exit-status.txt')]))
        self.assertFalse(ready['a'])
        self.assertEqual(report['required_failures'],
                         ['a/measure-exit-status.txt'])

    def test_blocked_dependency_cannot_appear_ready(self):
        """b's own artifact is perfect; its prerequisite is missing."""
        self.write('b/measure-exit-status.txt', '0\n')
        ready, report = self._ready(self._charter(
            [_spec('a/does-not-exist.txt')],
            [_spec('b/measure-exit-status.txt')]))
        self.assertTrue(report['tasks']['b']['ok'])   # b verified fine
        self.assertFalse(ready['b'])                  # but b is blocked
        self.assertFalse(ready['a'])
        self.assertEqual(report['not_ready'], ['a', 'b'])

    def test_failed_verification_cannot_appear_ready(self):
        self.write('a/measure-exit-status.txt', '1\n')
        self.write('b/measure-exit-status.txt', '0\n')
        ready, _ = self._ready(self._charter(
            [_spec('a/measure-exit-status.txt')],
            [_spec('b/measure-exit-status.txt')]))
        self.assertFalse(ready['a'])
        self.assertFalse(ready['b'])

    def test_readiness_never_exceeds_verification(self):
        self.write('a/measure-exit-status.txt', '1\n')
        self.write('b/measure-exit-status.txt', '0\n')
        _, report = self._ready(self._charter(
            [_spec('a/measure-exit-status.txt')],
            [_spec('b/measure-exit-status.txt')]))
        self.assertTrue(report['readiness_never_exceeds_verification'])
        self.assertTrue(report['two_verification_passes_agree'])

    def test_both_artifacts_present_and_zero_is_ready(self):
        self.write('a/measure-exit-status.txt', '0\n')
        self.write('b/measure-exit-status.txt', '0\n')
        ready, report = self._ready(self._charter(
            [_spec('a/measure-exit-status.txt')],
            [_spec('b/measure-exit-status.txt')]))
        self.assertTrue(ready['a'])
        self.assertTrue(ready['b'])
        self.assertTrue(report['ready_all'])
        self.assertEqual(report['required_failures'], [])

    @unittest.skipUnless(__import__('os').path.exists(
        'opencode-handoff/bundles'),
        'needs live evidence layout (bundles); run in full workspace')
    def test_repointing_a_real_task_at_a_missing_artifact_flips_readiness(self):
        """The demonstration required by the acceptance criterion."""
        charter = rp.load_charter(REAL_CHARTER)
        verifier = ArtifactVerifier(REPO_ROOT)
        before = verifier.verify_charter(charter)
        self.assertTrue(before['tasks']['p10-02']['ok'])
        self.assertTrue(before['plan']['ready']['p10-02'])

        broken = verify.repoint_evidence(
            charter, 'p10-02',
            'cura-loop/results/p10-02-annotation/DELETED.json')
        after = ArtifactVerifier(REPO_ROOT).verify_charter(broken)
        self.assertFalse(after['tasks']['p10-02']['ok'])
        self.assertFalse(after['plan']['ready']['p10-02'])
        # ...and everything downstream of it, which was ready before.
        for task_id in ('p10-03', 'p10-04'):
            self.assertTrue(before['plan']['ready'][task_id], task_id)
            self.assertFalse(after['plan']['ready'][task_id], task_id)
        # The charter on disk was not modified.
        self.assertEqual(json.loads(REAL_CHARTER.read_text())['baseline'],
                         charter['baseline'])


class RealCharterVerificationTests(unittest.TestCase):
    """Facts about the actual repository, asserted rather than narrated."""

    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.charter = rp.load_charter(REAL_CHARTER)
        cls.report = ArtifactVerifier(REPO_ROOT).verify_charter(cls.charter)

    def test_every_referenced_artifact_outside_p16_verifies(self):
        outside = [f for f in self.report['required_failures']
                   if not f.startswith('release-plan/')]
        self.assertEqual(outside, [])

    def test_all_automated_gates_are_met(self):
        automated = {gid: g for gid, g in self.report['gates'].items()
                     if not g['human_decision_required']}
        self.assertEqual(len(automated), 8)
        self.assertTrue(all(g['ok'] for g in automated.values()),
                        {k: v['reason'] for k, v in automated.items()
                         if not v['ok']})

    def test_both_human_gates_are_unmet_and_say_why(self):
        human = {gid: g for gid, g in self.report['gates'].items()
                 if g['human_decision_required']}
        self.assertEqual(sorted(human), ['G-USER-REVIEW-P07-P10',
                                         'G-USER-REVIEW-TRIO1'])
        for gate in human.values():
            self.assertFalse(gate['ok'])
            self.assertTrue(gate['reason'])

    def test_release_is_not_ready(self):
        self.assertFalse(self.report['ready_all'])
        self.assertTrue(set(self.report['not_ready']))

    def test_the_three_review_bundles_exist_and_are_hashed(self):
        bundles = [r for r in self.report['tasks']['bundle-p04']['artifacts']
                   ] + self.report['tasks']['bundle-p05']['artifacts'] \
            + self.report['tasks']['bundle-p06']['artifacts']
        self.assertEqual(len(bundles), 3)
        for record in bundles:
            self.assertTrue(record['ok'])
            self.assertTrue(record['path'].endswith('.zip'))
            self.assertGreater(record['size_bytes'], 100000)
            self.assertEqual(len(record['sha256']), 64)

    def test_verification_is_read_only(self):
        """The verifier must not create anything in the real repository."""
        before = sorted(p.relative_to(REPO_ROOT).as_posix()
                        for p in (REPO_ROOT / 'flow-ledger'
                                  / 'results').rglob('*'))
        ArtifactVerifier(REPO_ROOT).verify_charter(self.charter)
        after = sorted(p.relative_to(REPO_ROOT).as_posix()
                       for p in (REPO_ROOT / 'flow-ledger'
                                 / 'results').rglob('*'))
        self.assertEqual(before, after)

    def test_declared_and_verified_provenance_are_distinct(self):
        declared = rp.plan_effective(self.charter, rp.declared_resolve)
        self.assertEqual(declared['resolver'], 'declared_resolve')
        self.assertEqual(self.report['resolver'], 'verified')


if __name__ == '__main__':
    unittest.main()
