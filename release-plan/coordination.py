"""Coordination evidence for a release that had exactly one human (P16-03).

The acceptance rule for this card is negative: *do not invent a
cross-functional team for a solo project.* So the enforcement lives in the
data model, not in a disclaimer.

:class:`Roster` refuses a second human. Every "collaborator" in this release is
either

* the one human, wearing a named **role** (planner, implementer, tester,
  release engineer, documenter) - a hat, not a person;
* an **AI coding agent**, recorded as a tool with ``is_human=False`` and
  ``is_a_collaborator=False``, evidenced by real ``Co-Authored-By`` commit
  trailers; or
* an **external party** (QA, security, SRE, customer, stakeholder) recorded as
  ``NOT_APPLICABLE`` or ``BLOCKED`` with a reason and no participants.

:class:`DecisionLog`, :class:`RiskRegister` and :class:`CommunicationLog` all
resolve names against that roster, so a fabricated teammate cannot be written
down even by accident. Decisions require alternatives and a real source; risks
require an owner the roster actually contains; communications require
participants the roster actually contains.

``SPEC.md`` also asks that *overdue risks and missing owners are visible*.
:meth:`CoordinationRecord.visible_problems` reports them instead of hiding
them, and never treats a missing owner as acceptable.
"""
import hashlib
import json
import time
from pathlib import Path

DOCUMENT_PATH = Path(__file__).resolve().parent / 'coordination.json'

FABRICATED_TEAM_ERROR = (
    'this release had exactly one human; a second person cannot be recorded. '
    'Model the work as a role worn by the sole author, or record the external '
    'party as NOT_APPLICABLE/BLOCKED.')

EXTERNAL_STATUSES = frozenset({'NOT_APPLICABLE', 'BLOCKED'})
RISK_STATUSES = frozenset({'open', 'mitigated', 'accepted', 'closed', 'blocked'})
DECISION_STATUSES = frozenset({'made', 'superseded', 'reversed', 'proposed'})


class FabricatedTeamError(RuntimeError):
    """Raised when a record would imply a team that did not exist."""


class CoordinationError(ValueError):
    """Raised when a decision, risk or communication is under-evidenced."""


def _today():
    return time.strftime('%Y-%m-%d', time.gmtime())


class Roster:
    """Exactly one human, any number of roles, tools and external non-parties."""

    def __init__(self, human_id, name, email):
        if not name or not email:
            raise CoordinationError('the sole human needs a real name and email')
        self.human_id = human_id
        self.persons = {human_id: {
            'id': human_id, 'name': name, 'email': email, 'is_human': True,
            'is_a_collaborator': False,
            'cross_functional_teammate': False,
            'roles_worn': [],
            'note': 'sole human in this release; the git author of record'}}
        self.tools = {}
        self.external = {}

    # -- the one human -----------------------------------------------------
    def wear_role(self, role, evidence=None):
        """Record a role the sole author wore. A role is not a person."""
        if role in self.persons[self.human_id]['roles_worn']:
            return self.persons[self.human_id]
        self.persons[self.human_id]['roles_worn'].append(role)
        if evidence:
            self.persons[self.human_id].setdefault('role_evidence', {})[role] = \
                evidence
        return self.persons[self.human_id]

    def add_person(self, name, email=None, **_):
        """Always refused. There was one human."""
        raise FabricatedTeamError(FABRICATED_TEAM_ERROR)

    # -- tools -------------------------------------------------------------
    def add_tool(self, tool_id, kind, evidence, is_a_collaborator=False):
        if is_a_collaborator:
            raise FabricatedTeamError(
                'a tool cannot be recorded as a collaborator')
        self.tools[tool_id] = {'id': tool_id, 'kind': kind, 'is_human': False,
                               'is_a_collaborator': False,
                               'cross_functional_teammate': False,
                               'evidence': evidence}
        return self.tools[tool_id]

    # -- external non-parties ---------------------------------------------
    def add_external(self, external_id, function, status, reason,
                     contacted=False):
        if status not in EXTERNAL_STATUSES:
            raise CoordinationError(
                'an external party must be NOT_APPLICABLE or BLOCKED, not %r'
                % status)
        if contacted:
            raise FabricatedTeamError(
                'external party %r is recorded as %s; it cannot also have been '
                'contacted' % (external_id, status))
        if len(reason) < 20:
            raise CoordinationError(
                'external party %r needs a substantive reason' % external_id)
        self.external[external_id] = {
            'id': external_id, 'function': function, 'status': status,
            'reason': reason, 'is_human': None, 'participants': [],
            'cross_functional_teammate': False, 'contacted': False}
        return self.external[external_id]

    # -- queries -----------------------------------------------------------
    def contains(self, name):
        return (name in self.persons or name in self.tools
                or name in self.external)

    @property
    def distinct_humans(self):
        return [p['id'] for p in self.persons.values() if p['is_human']]

    def assert_no_fabricated_team(self):
        if len(self.distinct_humans) != 1:
            raise FabricatedTeamError(
                'expected exactly one human, found %r' % self.distinct_humans)
        for entry in list(self.persons.values()) + list(self.tools.values()):
            if entry.get('cross_functional_teammate'):
                raise FabricatedTeamError(
                    '%r is marked as a cross-functional teammate' % entry['id'])
            if entry.get('is_a_collaborator'):
                raise FabricatedTeamError(
                    '%r is marked as a collaborator' % entry['id'])
        for entry in self.external.values():
            if entry['status'] not in EXTERNAL_STATUSES or entry['participants']:
                raise FabricatedTeamError(
                    'external party %r is not honestly NOT_APPLICABLE/BLOCKED'
                    % entry['id'])
        return True

    def as_dict(self):
        return {'distinct_humans': len(self.distinct_humans),
                'human_ids': self.distinct_humans,
                'persons': dict(self.persons),
                'tools': dict(self.tools),
                'external_parties': dict(self.external),
                'roles_worn_by_sole_author':
                    list(self.persons[self.human_id]['roles_worn']),
                'cross_functional_team': False}


class DecisionLog:
    """Real decisions, each with alternatives, a source and one decider."""

    def __init__(self, roster):
        self.roster = roster
        self.entries = []

    def record(self, decision_id, date, title, decision, alternatives, reason,
               source, roles_worn=(), status='made', supersedes=None):
        if any(e['id'] == decision_id for e in self.entries):
            raise CoordinationError('duplicate decision id %r' % decision_id)
        if status not in DECISION_STATUSES:
            raise CoordinationError('unknown decision status %r' % status)
        if not alternatives:
            raise CoordinationError(
                'decision %r records no alternative; a decision with no '
                'alternative considered is not a decision' % decision_id)
        if not isinstance(source, dict) or not source.get('document'):
            raise CoordinationError('decision %r has no source' % decision_id)
        if len(reason) < 20:
            raise CoordinationError('decision %r has no substantive reason'
                                    % decision_id)
        for role in roles_worn:
            if role not in self.roster.persons[
                    self.roster.human_id]['roles_worn']:
                raise CoordinationError(
                    'decision %r credits role %r that the sole author is not '
                    'recorded as having worn' % (decision_id, role))
        if supersedes and not any(e['id'] == supersedes for e in self.entries):
            raise CoordinationError(
                'decision %r supersedes unknown decision %r'
                % (decision_id, supersedes))
        entry = {'id': decision_id, 'date': date, 'title': title,
                 'decision': decision, 'alternatives': list(alternatives),
                 'reason': reason, 'source': dict(source),
                 'decided_by': self.roster.human_id,
                 'distinct_humans_involved': 1,
                 'roles_worn': list(roles_worn), 'status': status,
                 'supersedes': supersedes}
        self.entries.append(entry)
        return entry

    def by_id(self, decision_id):
        for entry in self.entries:
            if entry['id'] == decision_id:
                return entry
        raise KeyError(decision_id)

    def superseded(self):
        return [e['supersedes'] for e in self.entries if e['supersedes']]


class RiskRegister:
    """Risks with a real owner, a status and a visible overdue check."""

    def __init__(self, roster):
        self.roster = roster
        self.entries = []

    def add(self, risk_id, risk, owner, status, likelihood, impact,
            mitigation, evidence, detected_at=None, review_due=None,
            due_basis=None):
        if any(e['id'] == risk_id for e in self.entries):
            raise CoordinationError('duplicate risk id %r' % risk_id)
        if status not in RISK_STATUSES:
            raise CoordinationError('unknown risk status %r' % status)
        if owner is None:
            pass    # recorded as unowned and surfaced by missing_owner()
        elif owner == '':
            raise CoordinationError(
                'risk %r has an empty owner; use None so it stays visible'
                % risk_id)
        elif not self.roster.contains(owner):
            raise FabricatedTeamError(
                'risk %r is owned by %r, who is not on the roster'
                % (risk_id, owner))
        if likelihood not in ('low', 'medium', 'high') or \
                impact not in ('low', 'medium', 'high'):
            raise CoordinationError('risk %r needs low/medium/high ratings'
                                    % risk_id)
        if review_due and not due_basis:
            raise CoordinationError(
                'risk %r declares a review_due date without saying where that '
                'date came from' % risk_id)
        entry = {'id': risk_id, 'risk': risk, 'owner': owner,
                 'status': status, 'likelihood': likelihood, 'impact': impact,
                 'mitigation': mitigation, 'evidence': evidence,
                 'detected_at': detected_at or _today(),
                 'review_due': review_due, 'due_basis': due_basis}
        self.entries.append(entry)
        return entry

    def overdue(self, as_of=None):
        as_of = as_of or _today()
        return [e['id'] for e in self.entries
                if e['review_due'] and e['review_due'] < as_of
                and e['status'] in ('open', 'blocked')]

    def missing_owner(self):
        return [e['id'] for e in self.entries if not e.get('owner')]


class CommunicationLog:
    """Communications that really happened, with their real artifacts."""

    def __init__(self, roster):
        self.roster = roster
        self.entries = []

    def record(self, comm_id, date, channel, direction, subject, participants,
               artifact=None, external_party=None, status='recorded',
               note=None):
        if any(e['id'] == comm_id for e in self.entries):
            raise CoordinationError('duplicate communication id %r' % comm_id)
        for name in participants:
            if not self.roster.contains(name):
                raise FabricatedTeamError(
                    'communication %r lists %r, who is not on the roster'
                    % (comm_id, name))
        if external_party is not None:
            party = self.roster.external.get(external_party)
            if party is None:
                raise CoordinationError(
                    'communication %r names unknown external party %r'
                    % (comm_id, external_party))
            if status not in EXTERNAL_STATUSES:
                raise CoordinationError(
                    'communication with an external party must be '
                    'NOT_APPLICABLE or BLOCKED, not %r' % status)
            if participants:
                raise FabricatedTeamError(
                    'communication %r is %s but lists participants'
                    % (comm_id, status))
        elif not participants:
            raise CoordinationError(
                'communication %r has no participants' % comm_id)
        if not artifact and status == 'recorded':
            raise CoordinationError(
                'communication %r has no artifact; an unrecorded communication '
                'cannot be claimed' % comm_id)
        entry = {'id': comm_id, 'date': date, 'channel': channel,
                 'direction': direction, 'subject': subject,
                 'participants': list(participants), 'artifact': artifact,
                 'external_party': external_party, 'status': status,
                 'note': note}
        self.entries.append(entry)
        return entry

    def with_external_parties(self):
        return [e for e in self.entries if e['external_party']]


class CoordinationRecord:
    """The whole coordination picture, exportable as evidence."""

    def __init__(self, roster, release_id, as_of=None):
        self.roster = roster
        self.release_id = release_id
        self.as_of = as_of or _today()
        self.decisions = DecisionLog(roster)
        self.risks = RiskRegister(roster)
        self.comms = CommunicationLog(roster)

    def visible_problems(self):
        """Overdue risks and missing owners, surfaced rather than hidden."""
        return {'as_of': self.as_of,
                'overdue_risks': self.risks.overdue(self.as_of),
                'risks_missing_owner': self.risks.missing_owner(),
                'unresolved_risks': [e['id'] for e in self.risks.entries
                                     if e['status'] in ('open', 'blocked')],
                'blocked_external_coordination':
                    [e['id'] for e in self.comms.with_external_parties()
                     if e['status'] == 'BLOCKED'],
                'not_applicable_external_coordination':
                    [e['id'] for e in self.comms.with_external_parties()
                     if e['status'] == 'NOT_APPLICABLE'],
                'decisions_awaiting_response':
                    [e['id'] for e in self.comms.entries
                     if e.get('note') == 'awaiting-response']}

    def audit(self):
        self.roster.assert_no_fabricated_team()
        return {
            'release_id': self.release_id,
            'distinct_humans': self.roster.as_dict()['distinct_humans'],
            'cross_functional_team': False,
            'roles_worn_by_sole_author':
                self.roster.as_dict()['roles_worn_by_sole_author'],
            'tools': sorted(self.roster.tools),
            'decisions': len(self.decisions.entries),
            'decisions_with_alternatives': sum(
                1 for e in self.decisions.entries if e['alternatives']),
            'decisions_superseding_an_earlier_one':
                sorted(set(self.decisions.superseded())),
            'risks': len(self.risks.entries),
            'communications': len(self.comms.entries),
            'communications_with_external_parties':
                len(self.comms.with_external_parties()),
            'problems': self.visible_problems(),
        }

    def export(self):
        return {'roster': self.roster.as_dict(),
                'decisions': list(self.decisions.entries),
                'risks': list(self.risks.entries),
                'communications': list(self.comms.entries),
                'audit': self.audit()}


def load_record(path=None, as_of=None):
    """Rebuild the real record *through* the enforced model.

    The JSON document is not trusted. Every entry is replayed through
    :class:`Roster`, :class:`DecisionLog`, :class:`RiskRegister` and
    :class:`CommunicationLog`, so a fabricated teammate, an unowned risk with a
    made-up owner, a decision with no alternative or a communication with an
    invented participant raises while loading.
    """
    document = json.loads(Path(path or DOCUMENT_PATH).read_text(
        encoding='utf-8'))
    spec = document['roster']
    human = spec['human']
    roster = Roster(human['id'], human['name'], human['email'])
    for entry in human.get('roles_worn', []):
        roster.wear_role(entry['role'], entry.get('evidence'))
    for tool in spec.get('tools', []):
        roster.add_tool(tool['id'], tool['kind'], tool['evidence'])
    for party in spec.get('external_parties', []):
        roster.add_external(party['id'], party['function'], party['status'],
                            party['reason'])

    record = CoordinationRecord(roster, document['release_id'],
                                as_of=as_of or document.get('as_of'))
    for entry in document['decisions']:
        kwargs = {k: v for k, v in entry.items()
                  if k in ('roles_worn', 'status', 'supersedes')}
        record.decisions.record(
            entry['id'], entry['date'], entry['title'], entry['decision'],
            entry['alternatives'], entry['reason'], entry['source'], **kwargs)
    for entry in document['risks']:
        kwargs = {k: v for k, v in entry.items()
                  if k in ('detected_at', 'review_due', 'due_basis')}
        record.risks.add(entry['id'], entry['risk'], entry.get('owner'),
                         entry['status'], entry['likelihood'], entry['impact'],
                         entry['mitigation'], entry['evidence'], **kwargs)
    for entry in document['communications']:
        kwargs = {k: v for k, v in entry.items()
                  if k in ('artifact', 'external_party', 'status', 'note')}
        record.comms.record(entry['id'], entry['date'], entry['channel'],
                            entry['direction'], entry['subject'],
                            entry['participants'], **kwargs)
    record.document_sha256 = hashlib.sha256(
        Path(path or DOCUMENT_PATH).read_bytes()).hexdigest()
    return record
