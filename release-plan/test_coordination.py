"""P16-03: coordination evidence that cannot describe a team that never existed."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import coordination
from coordination import (CoordinationError, CoordinationRecord,
                          FabricatedTeamError, Roster)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DOCUMENT = HERE / 'coordination.json'


def _roster():
    roster = Roster('owner', 'RedHolger', 'manuvashisth963@gmail.com')
    for role in ('authorizing-principal', 'planner', 'implementer', 'tester',
                 'release-engineer', 'documenter', 'self-reviewer'):
        roster.wear_role(role, 'evidence')
    roster.add_tool('opencode-agent', 'ai-coding-agent', 'commit trailers')
    roster.add_external('external-qa', 'independent QA review',
                        'NOT_APPLICABLE',
                        'no QA function existed in this solo release')
    return roster


def _record():
    return CoordinationRecord(_roster(), 'R1-trio1-review', as_of='2026-10-08')


def _commit_exists(sha):
    if not sha:
        return False
    return subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'cat-file', '-e', '%s^{commit}' % sha],
        capture_output=True, text=True).returncode == 0


class RosterEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.roster = _roster()

    def test_exactly_one_human(self):
        self.assertEqual(self.roster.distinct_humans, ['owner'])
        self.assertTrue(self.roster.assert_no_fabricated_team())

    def test_adding_a_second_human_always_raises(self):
        for name, email in [('Alice Chen', 'alice@example.com'),
                            ('QA Lead', 'qa@example.com'),
                            ('', ''), ('Bob', None)]:
            with self.assertRaises(FabricatedTeamError):
                self.roster.add_person(name, email)

    def test_a_second_human_injected_directly_is_caught_by_the_audit(self):
        self.roster.persons['intruder'] = {
            'id': 'intruder', 'name': 'Invented PM', 'is_human': True,
            'cross_functional_teammate': False, 'roles_worn': []}
        with self.assertRaises(FabricatedTeamError):
            self.roster.assert_no_fabricated_team()

    def test_a_tool_cannot_be_promoted_to_collaborator(self):
        with self.assertRaises(FabricatedTeamError):
            self.roster.add_tool('copilot', 'ai-coding-agent', 'x',
                                 is_a_collaborator=True)
        self.roster.add_tool('copilot', 'ai-coding-agent', 'trailer')
        self.assertFalse(self.roster.tools['copilot']['is_a_collaborator'])
        self.assertFalse(self.roster.tools['copilot']['is_human'])

    def test_marking_anyone_cross_functional_fails_the_audit(self):
        self.roster.persons['owner']['cross_functional_teammate'] = True
        with self.assertRaises(FabricatedTeamError):
            self.roster.assert_no_fabricated_team()

    def test_roles_are_hats_not_people(self):
        before = len(self.roster.persons)
        self.roster.wear_role('release-engineer')       # already worn
        self.roster.wear_role('on-call', 'evidence')    # new hat
        self.assertEqual(len(self.roster.persons), before)
        self.assertEqual(len(self.roster.distinct_humans), 1)
        self.assertIn('on-call',
                      self.roster.persons['owner']['roles_worn'])

    def test_external_party_must_be_not_applicable_or_blocked(self):
        with self.assertRaises(CoordinationError):
            self.roster.add_external('qa', 'QA', 'PARTICIPATED',
                                     'they reviewed everything carefully')
        with self.assertRaises(FabricatedTeamError):
            self.roster.add_external('qa', 'QA', 'NOT_APPLICABLE',
                                     'no QA function existed here',
                                     contacted=True)
        with self.assertRaises(CoordinationError):
            self.roster.add_external('qa', 'QA', 'NOT_APPLICABLE', 'nope')

    def test_human_needs_a_real_identity(self):
        with self.assertRaises(CoordinationError):
            Roster('owner', '', '')


class DecisionLogTests(unittest.TestCase):
    def setUp(self):
        self.record = _record()
        self.log = self.record.decisions

    def _record_decision(self, **overrides):
        kwargs = {'decision_id': 'D-1', 'date': '2026-10-08',
                  'title': 't', 'decision': 'd',
                  'alternatives': ['option b'],
                  'reason': 'a substantive reason for the decision',
                  'source': {'document': 'PLAN.md'},
                  'roles_worn': ['planner']}
        kwargs.update(overrides)
        return self.log.record(**kwargs)

    def test_a_decision_without_an_alternative_is_not_a_decision(self):
        with self.assertRaises(CoordinationError):
            self._record_decision(alternatives=[])

    def test_a_decision_without_a_source_is_rejected(self):
        with self.assertRaises(CoordinationError):
            self._record_decision(source={})
        with self.assertRaises(CoordinationError):
            self._record_decision(source='PLAN.md')

    def test_a_thin_reason_is_rejected(self):
        with self.assertRaises(CoordinationError):
            self._record_decision(reason='because')

    def test_an_unworn_role_cannot_be_credited(self):
        with self.assertRaises(CoordinationError):
            self._record_decision(roles_worn=['qa-lead'])

    def test_decided_by_is_always_the_one_human(self):
        entry = self._record_decision()
        self.assertEqual(entry['decided_by'], 'owner')
        self.assertEqual(entry['distinct_humans_involved'], 1)

    def test_duplicate_id_and_unknown_supersession_rejected(self):
        self._record_decision()
        with self.assertRaises(CoordinationError):
            self._record_decision()
        with self.assertRaises(CoordinationError):
            self._record_decision(decision_id='D-2', supersedes='D-9')

    def test_unknown_status_rejected(self):
        with self.assertRaises(CoordinationError):
            self._record_decision(status='vibing')


class RiskRegisterTests(unittest.TestCase):
    def setUp(self):
        self.record = _record()
        self.risks = self.record.risks

    def _add(self, **overrides):
        kwargs = {'risk_id': 'R-1', 'risk': 'r', 'owner': 'owner',
                  'status': 'open', 'likelihood': 'high', 'impact': 'high',
                  'mitigation': 'm', 'evidence': 'e'}
        kwargs.update(overrides)
        return self.risks.add(**kwargs)

    def test_an_owner_off_the_roster_is_a_fabrication(self):
        with self.assertRaises(FabricatedTeamError):
            self._add(owner='alice-qa')

    def test_empty_owner_rejected_but_none_is_recorded_and_surfaced(self):
        with self.assertRaises(CoordinationError):
            self._add(owner='')
        self._add(owner=None)
        self.assertEqual(self.risks.missing_owner(), ['R-1'])

    def test_overdue_is_computed_not_asserted(self):
        self._add(risk_id='R-due', review_due='2026-10-06',
                  due_basis='test basis for the due date')
        self._add(risk_id='R-future', review_due='2026-12-01',
                  due_basis='test basis for the due date')
        self._add(risk_id='R-closed', review_due='2026-10-01',
                  status='closed', due_basis='test basis for the due date')
        self.assertEqual(self.risks.overdue('2026-10-08'), ['R-due'])
        self.assertEqual(self.risks.overdue('2026-10-05'), [])

    def test_a_due_date_needs_a_stated_basis(self):
        with self.assertRaises(CoordinationError):
            self._add(review_due='2026-10-06')

    def test_bad_status_and_ratings_rejected(self):
        with self.assertRaises(CoordinationError):
            self._add(status='worried')
        with self.assertRaises(CoordinationError):
            self._add(likelihood='catastrophic')
        with self.assertRaises(CoordinationError):
            self._add(impact='severe')

    def test_duplicate_risk_id_rejected(self):
        self._add()
        with self.assertRaises(CoordinationError):
            self._add()


class CommunicationLogTests(unittest.TestCase):
    def setUp(self):
        self.record = _record()
        self.comms = self.record.comms

    def test_a_participant_off_the_roster_is_a_fabrication(self):
        with self.assertRaises(FabricatedTeamError):
            self.comms.record('C-1', '2026-10-08', 'standup', 'a -> b',
                              'daily sync', ['owner', 'alice-qa'],
                              artifact='notes.md')

    def test_an_invented_channel_with_no_artifact_is_rejected(self):
        with self.assertRaises(CoordinationError):
            self.comms.record('C-1', '2026-10-08', 'meeting', 'a -> b',
                              'review meeting', ['owner'])

    def test_external_communication_must_be_not_applicable_or_blocked(self):
        with self.assertRaises(CoordinationError):
            self.comms.record('C-1', '2026-10-08', 'email', 'a -> b',
                              'QA review', [], external_party='external-qa',
                              status='recorded')

    def test_a_blocked_external_communication_has_no_participants(self):
        with self.assertRaises(FabricatedTeamError):
            self.comms.record('C-1', '2026-10-08', 'none', 'none',
                              'QA review', ['owner'],
                              external_party='external-qa',
                              status='NOT_APPLICABLE')

    def test_unknown_external_party_rejected(self):
        with self.assertRaises(CoordinationError):
            self.comms.record('C-1', '2026-10-08', 'none', 'none', 'x', [],
                              external_party='external-legal',
                              status='NOT_APPLICABLE')

    def test_internal_communication_with_no_participants_rejected(self):
        with self.assertRaises(CoordinationError):
            self.comms.record('C-1', '2026-10-08', 'document', 'a -> b', 'x',
                              [], artifact='PLAN.md')


class RealRecordTests(unittest.TestCase):
    """Facts asserted about the real coordination.json document."""

    @classmethod
    def setUpClass(cls):
        __import__('history_gate').require_full_history()
        cls.record = coordination.load_record(DOCUMENT)
        cls.audit = cls.record.audit()

    def test_document_replays_through_the_enforced_model(self):
        self.assertEqual(self.audit['distinct_humans'], 1)
        self.assertFalse(self.audit['cross_functional_team'])
        self.assertEqual(self.record.roster.as_dict()['distinct_humans'], 1)

    def test_the_sole_human_is_the_real_git_author(self):
        person = self.record.roster.persons['owner']
        self.assertEqual(person['email'], 'manuvashisth963@gmail.com')
        out = subprocess.run(
            ['git', '-C', str(REPO_ROOT), 'log', '--format=%ae'],
            capture_output=True, text=True).stdout.split()
        self.assertIn(person['email'], set(out))
        self.assertEqual(len(set(out)), 2)   # RedHolger + the manu@local alias

    def test_roles_are_hats_worn_by_one_person_and_each_is_evidenced(self):
        person = self.record.roster.persons['owner']
        self.assertEqual(len(person['roles_worn']), 7)
        self.assertEqual(len(person['role_evidence']), 7)
        self.assertIn('self-reviewer', person['roles_worn'])
        self.assertIn('not independent review',
                      person['role_evidence']['self-reviewer'])

    def test_agents_are_tools_not_collaborators(self):
        tools = self.record.roster.tools
        self.assertIn('opencode-agent', tools)
        self.assertIn('copilot-agent', tools)
        for tool in tools.values():
            self.assertFalse(tool['is_human'])
            self.assertFalse(tool['is_a_collaborator'])
            self.assertTrue(tool['evidence'])

    def test_all_external_coordination_is_not_applicable_or_blocked(self):
        external = self.record.roster.external
        self.assertEqual(len(external), 5)
        self.assertTrue(all(p['status'] in ('NOT_APPLICABLE', 'BLOCKED')
                            for p in external.values()))
        self.assertTrue(all(p['participants'] == []
                            for p in external.values()))
        self.assertEqual(external['study-participants']['status'], 'BLOCKED')

    def test_decision_log_is_real_and_complete(self):
        decisions = self.record.decisions.entries
        self.assertEqual(len(decisions), 14)
        self.assertEqual(self.audit['decisions_with_alternatives'], 14)
        for entry in decisions:
            self.assertEqual(entry['decided_by'], 'owner')
            self.assertEqual(entry['distinct_humans_involved'], 1)
            self.assertTrue(entry['source']['document'])
            self.assertGreaterEqual(len(entry['alternatives']), 1)

    def test_the_two_required_real_decisions_are_present(self):
        by_id = {e['id']: e for e in self.record.decisions.entries}
        batch = by_id['DEC-004']
        self.assertEqual(batch['date'], '2026-10-05')
        self.assertIn('one continuous batch', batch['decision'])
        self.assertEqual(batch['source']['commit'], '29908c6')
        self.assertEqual(batch['supersedes'], 'DEC-002')
        apple = by_id['DEC-005']
        self.assertIn('AppleDouble', apple['title'])
        self.assertIn('ExFAT', apple['reason'])
        self.assertEqual(apple['source']['commit'], '9830718')

    def test_every_decision_commit_really_exists_in_this_repository(self):
        commits = [e['source'].get('commit')
                   for e in self.record.decisions.entries]
        named = [c for c in commits if c]
        self.assertGreaterEqual(len(named), 8)
        for sha in named:
            self.assertTrue(_commit_exists(sha), sha)

    def test_uncommitted_authorization_is_labelled_as_such(self):
        dec = self.record.decisions.by_id('DEC-009')
        self.assertIsNone(dec['source']['commit'])
        self.assertIn('UNCOMMITTED', dec['source']['commit_note'])

    def test_risk_register_is_real_and_visible(self):
        risks = self.record.risks.entries
        self.assertEqual(len(risks), 11)
        problems = self.record.visible_problems()
        self.assertEqual(problems['overdue_risks'], ['R-02'])
        self.assertEqual(problems['risks_missing_owner'], ['R-11'])
        self.assertIn('R-01', problems['unresolved_risks'])
        by_id = {e['id']: e for e in risks}
        self.assertEqual(by_id['R-04']['status'], 'accepted')
        self.assertEqual(by_id['R-07']['status'], 'blocked')
        self.assertIsNone(by_id['R-11']['owner'])
        self.assertTrue(by_id['R-02']['due_basis'])

    def test_communications_are_real_and_externals_are_honest(self):
        comms = self.record.comms.entries
        self.assertEqual(len(comms), 11)
        internal = [c for c in comms if not c['external_party']]
        external = self.record.comms.with_external_parties()
        self.assertEqual(len(internal), 6)
        self.assertEqual(len(external), 5)
        for entry in internal:
            self.assertEqual(entry['participants'], ['owner'] if len(
                entry['participants']) == 1 else ['owner', 'opencode-agent'])
            self.assertTrue(entry['artifact'])
        self.assertTrue(all(c['status'] in ('NOT_APPLICABLE', 'BLOCKED')
                            for c in external))
        self.assertTrue(all(c['participants'] == [] for c in external))

    def test_no_record_names_anyone_off_the_roster(self):
        names = set()
        for entry in self.record.decisions.entries:
            names.add(entry['decided_by'])
        for entry in self.record.risks.entries:
            if entry['owner']:
                names.add(entry['owner'])
        for entry in self.record.comms.entries:
            names.update(entry['participants'])
        for name in names:
            self.assertTrue(self.record.roster.contains(name), name)
        # Decisions and risk ownership are human acts: only the one human.
        deciders = {e['decided_by'] for e in self.record.decisions.entries}
        owners = {e['owner'] for e in self.record.risks.entries if e['owner']}
        self.assertEqual(deciders, {'owner'})
        self.assertEqual(owners, {'owner'})
        # Anything else named is a tool, never a second person.
        self.assertTrue(names - {'owner'} <= set(self.record.roster.tools))
        self.assertEqual(names - {'owner'}, {'opencode-agent'})

    def test_export_is_json_serialisable_and_complete(self):
        exported = self.record.export()
        text = json.dumps(exported, sort_keys=True)
        self.assertEqual(len(json.loads(text)['decisions']), 14)
        self.assertEqual(exported['audit']['distinct_humans'], 1)
        self.assertEqual(len(self.record.document_sha256), 64)

    def test_the_document_rejects_an_inserted_teammate(self):
        raw = json.loads(DOCUMENT.read_text(encoding='utf-8'))
        tampered = copy.deepcopy(raw)
        tampered['risks'][0]['owner'] = 'alice-qa'
        handle = Path(tempfile.mkdtemp(prefix='p16-03-')) / 'tampered.json'
        handle.write_text(json.dumps(tampered), encoding='utf-8')
        self.addCleanup(shutil.rmtree, handle.parent, True)
        with self.assertRaises(FabricatedTeamError):
            coordination.load_record(handle)


if __name__ == '__main__':
    unittest.main()
