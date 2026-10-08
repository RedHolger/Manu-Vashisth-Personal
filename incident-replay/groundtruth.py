"""Ground truth for the P12 corpus — labels live here and nowhere else.

The discipline is the P10 `Oracle` one: an analyst annotation is a separate
artifact from the evidence, and it reaches the scoring code only through
:func:`reveal`. Neither `ingest.py` nor `detect.py` imports this module, so a
detector cannot see a label even by accident; `test_evaluate.py` asserts that
by scanning the sources.

Each scenario is annotated by naming the **attack session**: the events that
constitute the intrusion are exactly the events carrying that `session_id`.
That is how a human analyst would mark it up (one hijacked session), and it
keeps the label table legible instead of a wall of event ids. Benign
look-alikes carry `attack_session=None` and therefore have an empty attack
set — they are not "attacks we failed to find", they are legitimate activity
that resembles an attack, and a detector firing on them is a false positive.

Two extra annotations matter for honesty downstream:

* ``absent_event_ids`` — ids the scenario declares but that reach no source
  file (rotation loss). A finding must never cite these as support; they can
  only be cited as an investigative gap.
* ``benign_rationale`` — why the look-alike is legitimate, so a reviewer can
  check the label rather than trust it.
"""
import scenarios

GROUND_TRUTH = {
    'm01-credstuff-exfil': {
        'malicious': True,
        'attack_kind': 'credential guessing followed by bulk exfiltration',
        'attack_session': 's-m01-attacker',
        'actor_ip': '203.0.113.44',
        'victim_actor': 'u-1042',
        'narrative': 'Nine password rejections from an IP that is not in the '
                     'asset baseline for u-1042, then a success from the same '
                     'IP, an object listing of customer-db and fourteen '
                     '60 MB part downloads (840 MB total) inside 18 minutes. '
                     'The edge VPN concentrator — the sole source for the '
                     'tunnel events — brackets the session.',
        'benign_lookalike_of': None,
        'benign_rationale': None,
    },
    'm02-validcreds-staged-exfil': {
        'malicious': True,
        'attack_kind': 'valid-credential abuse with privilege grant and '
                       'staged exfiltration',
        'attack_session': 's-m02-attacker',
        'actor_ip': '198.18.7.9',
        'victim_actor': 'u-2077',
        'narrative': 'No authentication failures at all: a password-only '
                     'login at 02:14 UTC from an unbaselined IP, a '
                     'permission_grant of role:data-reader, an object listing '
                     'of finance-shares, then twelve 400 MB downloads '
                     '(4.8 GB total). A burst-failure rule has nothing to '
                     'match here.',
        'benign_lookalike_of': None,
        'benign_rationale': None,
    },
    'm03-slow-credstuff': {
        'malicious': True,
        'attack_kind': 'low-and-slow credential guessing followed by '
                       'exfiltration',
        'attack_session': 's-m03-attacker',
        'actor_ip': '203.0.113.90',
        'victim_actor': 'u-3311',
        'narrative': 'Six password rejections spread over 240 s — inside the '
                     'reference rule\'s 300 s window but slow enough to look '
                     'like a human mistyping — then a success, an hr-records '
                     'listing and eight 90 MB downloads (720 MB total).',
        'benign_lookalike_of': None,
        'benign_rationale': None,
    },
    'm04-insider-known-ip-bulk': {
        'malicious': True,
        'attack_kind': 'insider bulk export from a baselined IP with no '
                       'change ticket',
        'attack_session': 's-m04-insider',
        'actor_ip': '198.51.100.77',
        'victim_actor': 'u-4402',
        'narrative': 'A single password-only login from the actor\'s own '
                     'baselined IP, an engineering-src listing and ten '
                     '250 MB exports (2.5 GB total) starting 22:50 UTC with '
                     'no ticket reference anywhere in the session. Both '
                     'detectors are expected to miss this: no failures, and '
                     'the source IP is baselined.',
        'benign_lookalike_of': None,
        'benign_rationale': None,
    },
    'b01-admin-bulk-restore': {
        'malicious': False,
        'attack_kind': None,
        'attack_session': None,
        'actor_ip': '198.51.100.10',
        'victim_actor': 'svc-backup',
        'narrative': 'A workload identity performs a ticketed restore: '
                     'CHG-4821 is opened first, then forty 150 MB downloads '
                     '(6 GB total) from a baselined IP over 2.5 hours.',
        'benign_lookalike_of': 'bulk exfiltration (volume exceeds every '
                               'malicious scenario except m02)',
        'benign_rationale': 'The egress volume is larger than any attack in '
                            'the corpus, so a volume-only detector must flag '
                            'it. It is legitimate because the source IP is in '
                            'the asset baseline for svc-backup, the identity '
                            'is a non-interactive workload, and a change '
                            'ticket is opened in the same session before any '
                            'data is read.',
    },
    'b02-password-expiry-retries': {
        'malicious': False,
        'attack_kind': None,
        'attack_session': None,
        'actor_ip': '198.51.100.44',
        'victim_actor': 'u-5510',
        'narrative': 'Four password rejections over 40 s from the user\'s own '
                     'baselined laptop, then a success presenting password '
                     'and TOTP, then two 1 MB report downloads.',
        'benign_lookalike_of': 'credential guessing followed by a successful '
                               'login',
        'benign_rationale': 'The failure burst satisfies the reference rule '
                            '(>=3 failures then success inside 300 s), so '
                            'that rule must produce a false positive here. It '
                            'is legitimate because the source IP is baselined '
                            'for this actor, the successful login presents a '
                            'second factor, and the egress that follows is '
                            '2 MB.',
    },
    'b03-helpdesk-unlock-burst': {
        'malicious': False,
        'attack_kind': None,
        'attack_session': None,
        'actor_ip': '198.51.100.9',
        'victim_actor': 'svc-helpdesk',
        'narrative': 'A helpdesk workload identity produces five password '
                     'rejections in 25 s while verifying an account unlock, '
                     'then logs in and opens INC-90117. No data plane at all.',
        'benign_lookalike_of': 'credential guessing followed by a successful '
                               'login',
        'benign_rationale': 'Five failures then a success is exactly the '
                            'reference rule\'s signature, so it must produce '
                            'a false positive. It is legitimate because the '
                            'identity is a baselined non-interactive workload, '
                            'the session opens a ticket, and zero bytes leave '
                            'the system.',
    },
    'b04-quarterly-report-export': {
        'malicious': False,
        'attack_kind': None,
        'attack_session': None,
        'actor_ip': '198.51.100.61',
        'victim_actor': 'u-6620',
        'narrative': 'A finance user opens CHG-4830, logs in with password '
                     'and TOTP from a baselined IP, exports one 320 MB '
                     'workbook and downloads three 5 MB reports.',
        'benign_lookalike_of': 'staged bulk export',
        'benign_rationale': 'A single large export looks like the first stage '
                            'of exfiltration. It is legitimate because the '
                            'source IP is baselined, a ticket precedes the '
                            'export in the same session, a second factor was '
                            'presented, and total egress (335 MB) is inside '
                            'the actor\'s normal daily volume.',
    },
    'b05-vpn-reconnect-retries': {
        'malicious': False,
        'attack_kind': None,
        'attack_session': None,
        'actor_ip': '198.51.100.88',
        'victim_actor': 'u-7731',
        'narrative': 'Six password rejections over 100 s from a baselined IP '
                     'while a VPN client renegotiates, then a success '
                     'presenting password and TOTP. No data plane.',
        'benign_lookalike_of': 'credential guessing followed by a successful '
                               'login',
        'benign_rationale': 'The longest failure burst in the corpus, so the '
                            'reference rule must fire and produce a false '
                            'positive. It is legitimate because the source IP '
                            'is baselined, the success presents a second '
                            'factor, and nothing is read afterwards.',
    },
}


def scenario_ids():
    return list(scenarios.SCENARIO_IDS)


def labels():
    """Deep-ish copy of the annotation table (evaluation-only)."""
    return {sid: dict(entry) for sid, entry in GROUND_TRUTH.items()}


def reveal(sids):
    """The only sanctioned path from labels to the scorer.

    Returned entries carry the derived ``attack_event_ids`` and
    ``absent_event_ids`` so the scorer never has to reach back into the
    scenario builders.
    """
    table = labels()
    unknown = [sid for sid in sids if sid not in table]
    if unknown:
        raise KeyError('unlabeled scenarios %r' % (unknown,))
    for sid in sids:
        table[sid]['attack_event_ids'] = attack_event_ids(sid)
        table[sid]['absent_event_ids'] = absent_event_ids(sid)
    return {sid: table[sid] for sid in sids}


def is_malicious(scenario_id):
    return GROUND_TRUTH[scenario_id]['malicious']


def malicious_ids():
    return sorted(sid for sid in GROUND_TRUTH if is_malicious(sid))


def benign_ids():
    return sorted(sid for sid in GROUND_TRUTH if not is_malicious(sid))


def attack_event_ids(scenario_id):
    """Event ids annotated as part of the intrusion (empty when benign)."""
    entry = GROUND_TRUTH[scenario_id]
    session = entry['attack_session']
    if session is None:
        return []
    events, _ = scenarios.logical_events(scenario_id)
    return [event['id'] for event in events
            if event['session_id'] == session]


def attack_event_ids_in_evidence(scenario_id, timeline):
    """Attack ids that actually reached a source file (citable evidence)."""
    present = timeline.ids()
    return [event_id for event_id in attack_event_ids(scenario_id)
            if event_id in present]


def absent_event_ids(scenario_id):
    """Declared-but-lost ids; citable only as an investigative gap."""
    return scenarios.absent_event_ids(scenario_id)


def attack_totals():
    return {sid: len(attack_event_ids(sid)) for sid in malicious_ids()}


def splits(seed=None):
    """Ground truth arranged by the fixed hashed dev/held-out split."""
    partition = scenarios.split(seed=seed) if seed is not None \
        else scenarios.split()
    return {name: {sid: dict(GROUND_TRUTH[sid], attack_event_ids=
                              attack_event_ids(sid))
                   for sid in partition[name]}
            for name in ('dev', 'held_out')}


def integrity_report():
    """Self-check of the annotation table (used by the measure script)."""
    problems = []
    for sid in scenarios.SCENARIO_IDS:
        if sid not in GROUND_TRUTH:
            problems.append('%s is unlabeled' % sid)
            continue
        entry = GROUND_TRUTH[sid]
        ids = attack_event_ids(sid)
        if entry['malicious'] and not ids:
            problems.append('%s is malicious but annotates no attack events'
                            % sid)
        if not entry['malicious'] and ids:
            problems.append('%s is benign but annotates attack events' % sid)
        if entry['malicious'] and not entry.get('attack_kind'):
            problems.append('%s is malicious without an attack_kind' % sid)
        if not entry['malicious'] and not entry.get('benign_rationale'):
            problems.append('%s is benign without a benign_rationale' % sid)
        if not entry['malicious'] and not entry.get('benign_lookalike_of'):
            problems.append('%s is benign without benign_lookalike_of' % sid)
    overlap = set(malicious_ids()) & set(benign_ids())
    if overlap:
        problems.append('a scenario is labeled both ways: %r' % overlap)
    return {'scenarios': len(scenarios.SCENARIO_IDS),
            'malicious': len(malicious_ids()),
            'benign': len(benign_ids()),
            'attack_events': sum(len(attack_event_ids(sid))
                                 for sid in malicious_ids()),
            'absent_events': sum(len(absent_event_ids(sid))
                                 for sid in scenario_ids()),
            'problems': problems}
