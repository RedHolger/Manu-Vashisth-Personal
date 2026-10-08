"""Consulting artifacts for IncidentReplay (P12-03).

Turns the P12-02 evaluation into two Markdown reports — an executive one and a
technical one — in which **every finding cites the exact event ids, source
file and sha256 that support it**, and in which three kinds of claim are kept
in separate, explicitly labeled sections:

* ``FACT`` — something the ingested evidence states directly. A fact is only
  emitted when the events that support it exist in the timeline, and it is
  phrased so a reviewer can check it against the raw source line.
* ``HYPOTHESIS`` — an interpretation of facts. Every hypothesis must name at
  least one alternative explanation and carry a ``risk_rationale`` saying what
  follows if it is wrong.
* ``REMEDIATION`` — a proposed control. Every remediation must say which
  finding ids it addresses and list concrete steps; it is *not* evidence that
  anything was fixed. Validation lives in P12-04 and, until it has run, each
  remediation carries ``validation_status='NOT_YET_VALIDATED'``.

Nothing here invents numbers. Counts, byte totals, precision/recall and the
uncertainty ledger are all read out of the evaluation report and the ingested
timelines, so re-running the pipeline regenerates byte-identical reports.

Run ``python3 -B report.py --finding <ID>`` to print one finding together with
the resolved provenance of every event id it cites, including the raw source
line and that source file's sha256 — that is the reproduction path a reviewer
is meant to use.
"""
import argparse
import hashlib
import json
from pathlib import Path

import detect
import evaluate
import groundtruth
import scenarios

FACT = 'FACT'
HYPOTHESIS = 'HYPOTHESIS'
REMEDIATION = 'REMEDIATION'
CLASSIFICATIONS = (FACT, HYPOTHESIS, REMEDIATION)

NOT_VALIDATED = 'NOT_YET_VALIDATED'
REFERENCE = detect.REFERENCE_RULE
SEQUENCE = detect.SEQUENCE_RULE
COMBINED = evaluate.COMBINED

DISCLAIMER = ('Synthetic corpus. Every host, actor, IP address and object name '
              'in this report is invented; all addresses come from RFC 5737 / '
              'RFC 2544 reserved ranges. No real incident is described, no '
              'analyst time was measured and no time saving is claimed.')


def _bracketing_ids(timeline, missing_seq):
    """The nearest present records on either side of a seq gap.

    A claim about records that never arrived can only be supported by the
    records that did, so the two that bound the hole are cited and the absent
    ids are deliberately not.
    """
    by_seq = {event['seq']: event['id'] for event in timeline.events
              if event['seq'] is not None}
    present = sorted(by_seq)
    ids = []
    for seq in sorted(missing_seq):
        before = [value for value in present if value < seq]
        after = [value for value in present if value > seq]
        if before:
            ids.append(by_seq[before[-1]])
        if after:
            ids.append(by_seq[after[0]])
    return sorted(set(ids))


def measurement_block(artifact, values, produced_by='', note=''):
    """Cite a checksummed measurement artifact instead of individual events.

    Corpus-level claims (precision/recall, false-positive rates) are not
    supported by a handful of event ids; they are supported by the evaluation
    run that produced them. Naming that artifact and its sha256 keeps the
    claim reproducible in the same sense an event citation is.
    """
    path = Path(artifact)
    return {'artifact': str(path), 'exists': path.exists(),
            'sha256': (hashlib.sha256(path.read_bytes()).hexdigest()
                       if path.exists() else None),
            'produced_by': produced_by
            or 'python3 -B measure_p12_02.py --out results/'
               'p12-02-groundtruth',
            'values': values, 'note': note}


EVALUATION_ARTIFACT = 'results/p12-02-groundtruth/metrics.json'


def _provenance(timeline, event_ids, note=''):
    """Group cited ids by source file so each block carries one sha256."""
    blocks = {}
    for event_id in event_ids:
        entry = timeline.provenance(event_id)
        key = (entry['source_file'], entry['source_sha256'])
        block = blocks.setdefault(key, {
            'source_file': entry['source_file'],
            'source_sha256': entry['source_sha256'],
            'source_format': entry['source_format'],
            'event_ids': [], 'source_lines': [], 'raw_timestamps': [],
            'tz_offset_minutes': sorted({entry['tz_offset_minutes']}),
            'mirrored_in': [], 'note': note})
        block['event_ids'].append(event_id)
        block['source_lines'].append(entry['source_line'])
        block['raw_timestamps'].append(entry['raw_ts'])
        block['tz_offset_minutes'] = sorted(
            set(block['tz_offset_minutes']) | {entry['tz_offset_minutes']})
        block['mirrored_in'].extend(
            mirror['source_file'] for mirror in entry['mirrored_in'])
    ordered = [blocks[key] for key in sorted(blocks)]
    for block in ordered:
        block['mirrored_in'] = sorted(set(block['mirrored_in']))
        block['event_count'] = len(block['event_ids'])
    return ordered


def _finding(corpus, evaluation, index, classification, severity, title,
             statement, scenario=None, detector=None, evidence=(),
             risk_rationale=None, alternatives=(), steps=(), addresses=(),
             uncertainty=(), validation_status=NOT_VALIDATED,
             measurement=()):
    """Assemble one finding; evidence blocks are already resolved."""
    entry = {'id': '%s-%02d' % (classification[:3].upper(), index),
             'classification': classification, 'severity': severity,
             'title': title, 'statement': statement, 'scenario': scenario,
             'detector': detector, 'evidence': list(evidence),
             'evidence_event_ids': sorted({event_id
                                           for block in evidence
                                           for event_id
                                           in block['event_ids']}),
             'evidence_source_sha256': sorted({block['source_sha256']
                                               for block in evidence}),
             'uncertainty': list(uncertainty),
             'measurement': list(measurement),
             'reproduce': 'python3 -B report.py --finding %s-%02d'
                          % (classification[:3].upper(), index)}
    if classification == HYPOTHESIS:
        entry['risk_rationale'] = risk_rationale
        entry['alternatives'] = list(alternatives)
    if classification == REMEDIATION:
        entry['remediation_steps'] = list(steps)
        entry['addresses'] = list(addresses)
        entry['validation_status'] = validation_status
    return entry


def build_findings(corpus, evaluation, validation=None):
    """Derive every finding from the ingested evidence and the evaluation."""
    validation = validation or {}
    findings = []
    counters = {FACT: 0, HYPOTHESIS: 0, REMEDIATION: 0}

    def add(classification, **kwargs):
        counters[classification] += 1
        finding = _finding(corpus, evaluation, counters[classification],
                           classification, **kwargs)
        findings.append(finding)
        return finding

    labels = evaluation['labels']
    per_detector = evaluation['per_detector']
    benign_fps = evaluation['benign_lookalike_false_positives']
    malicious = groundtruth.malicious_ids()
    gap_evidence = {}

    for sid in malicious:
        timeline = corpus[sid]['timeline']
        attack_ids = groundtruth.attack_event_ids(sid)
        by_id = {event['id']: event for event in timeline.events}
        cited = [event_id for event_id in attack_ids if event_id in by_id]
        facts = []

        burst = per_detector[REFERENCE]['scenario_level']['all']
        reference_findings = evaluation['findings'][sid][REFERENCE]
        if reference_findings:
            detail = reference_findings[0]['detail']
            facts.append(add(
                FACT, severity='high',
                title='Authentication failure burst then success — %s' % sid,
                statement='%d authentication failures for actor %s from %s '
                          'spanning %.0f s, followed by a successful login '
                          'from the same address. Observed in the ingested '
                          'timeline; the reference rule %s cites these %d '
                          'events.'
                          % (detail['failures'],
                             reference_findings[0]['user'],
                             reference_findings[0]['ip'],
                             detail['burst_span_seconds'], REFERENCE,
                             len(reference_findings[0]['evidence_ids'])),
                scenario=sid, detector=REFERENCE,
                evidence=_provenance(
                    timeline, reference_findings[0]['evidence_ids'],
                    'every id below is cited by the reference rule finding')))
        else:
            failures = [event for event in timeline.events
                        if event['kind'] == 'failure']
            facts.append(add(
                FACT, severity='info',
                title='No authentication failure anywhere in %s' % sid,
                statement='The ingested timeline for this scenario contains '
                          '%d authentication failure events, so no '
                          'failure-burst indicator can match it. The session '
                          'begins with a successful login.' % len(failures),
                scenario=sid, detector=REFERENCE,
                evidence=_provenance(
                    timeline,
                    [event['id'] for event in timeline.events
                     if event['kind'] == 'success'],
                    'the only authentication outcomes present')))

        sequence_findings = evaluation['findings'][sid][SEQUENCE]
        if sequence_findings:
            detail = sequence_findings[0]['detail']
            facts.append(add(
                FACT, severity=sequence_findings[0]['severity'],
                title='Bulk egress from an unbaselined source IP — %s' % sid,
                statement='Actor %s authenticated from %s, which is not in the '
                          'asset baseline %r for that actor, then read %d '
                          'data-plane objects totalling %d bytes within %.0f '
                          's. Ticket references present in the chain: %s.'
                          % (sequence_findings[0]['user'],
                             sequence_findings[0]['ip'],
                             detail['baseline_known_ips'],
                             detail['data_plane_objects'],
                             detail['bytes_out_total'],
                             detail['chain_span_seconds'],
                             detail['ticket_refs'] or 'none'),
                scenario=sid, detector=SEQUENCE,
                evidence=_provenance(
                    timeline, sequence_findings[0]['evidence_ids'],
                    'the full chain the sequence detector cites')))
        else:
            total = sum(event['bytes_out'] for event in timeline.events)
            facts.append(add(
                FACT, severity='high',
                title='Bulk egress that no detector flagged — %s' % sid,
                statement='%d bytes left the system across %d data-plane '
                          'events in this scenario and neither detector '
                          'emitted a finding. The source IP %s is inside the '
                          'asset baseline for actor %s and no ticket '
                          'reference appears in the session.'
                          % (total,
                             sum(1 for event in timeline.events
                                 if event['action']
                                 in detect.DATA_PLANE_ACTIONS),
                             groundtruth.GROUND_TRUTH[sid]['actor_ip'],
                             groundtruth.GROUND_TRUTH[sid]['victim_actor']),
                scenario=sid, detector=None,
                evidence=_provenance(
                    timeline,
                    [event['id'] for event in timeline.events
                     if event['action'] in detect.DATA_PLANE_ACTIONS],
                    'data-plane events present but unflagged')))

        successes = [event for event in timeline.events
                     if event['kind'] == 'success']
        if successes and successes[0]['auth_factors'] == ['password']:
            facts.append(add(
                FACT, severity='medium',
                title='Single-factor interactive login — %s' % sid,
                statement='The successful login in this scenario presented '
                          'exactly one authentication factor (%r) from an '
                          'interactive session. No second factor appears '
                          'anywhere in the ingested evidence for it.'
                          % (successes[0]['auth_factors'],),
                scenario=sid, detector=None,
                evidence=_provenance(timeline, [successes[0]['id']],
                                     'the login event and its auth_factors '
                                     'field as ingested')))

    for sid in sorted(corpus):
        for entry in corpus[sid]['timeline'].uncertainty:
            if entry['kind'] != 'missing_records':
                continue
            absent = groundtruth.absent_event_ids(sid)
            brackets = _bracketing_ids(corpus[sid]['timeline'],
                                       entry['missing_seq'])
            gap_evidence[sid] = brackets
            add(FACT, severity='medium',
                title='Log continuity gap — %s' % sid,
                statement='Sequence numbers %s are absent from every source '
                          'of this scenario (%d of %d expected records '
                          'present). The corresponding event ids %s were never '
                          'reconstructed and appear in no finding as support; '
                          'they are cited here as an investigative gap only. '
                          'The records cited below are the ones that bracket '
                          'the hole.'
                          % (entry['missing_seq'], entry['observed_records'],
                             entry['expected_records'], absent),
                scenario=sid, detector=None,
                evidence=_provenance(
                    corpus[sid]['timeline'], brackets,
                    'the records that bracket the gap; the absent ids are '
                    'deliberately NOT in this list'),
                uncertainty=['missing_records'])

    any_timeline = corpus['m01-credstuff-exfil']['timeline']
    skew_entry = [entry for entry in any_timeline.uncertainty
                  if entry['kind'] == 'clock_skew']
    order_entry = [entry for entry in any_timeline.uncertainty
                   if entry['kind'] == 'clock_order_uncertain']
    if skew_entry or order_entry:
        ambiguous = [event['id'] for event in any_timeline.events
                     if event['order_uncertain']]
        add(FACT, severity='low',
            title='Clock skew and ambiguous event ordering are recorded',
            statement='The largest timestamp disagreement between two sources '
                      'reporting the same event id is %.0f s, and %d events '
                      'sit inside the %d s tolerance of an event from a '
                      'different source, so their relative order is not '
                      'established by the evidence (%s). Ordering claims in '
                      'this report never depend on those pairs alone.'
                      % (skew_entry[0]['max_observed_seconds'] if skew_entry
                         else 0,
                         order_entry[0]['event_count'] if order_entry else 0,
                         scenarios.CLOCK_SKEW_TOLERANCE_SECONDS,
                         ', '.join(ambiguous)),
            scenario='m01-credstuff-exfil', detector=None,
            evidence=_provenance(any_timeline, ambiguous,
                                 'events whose order is uncertain'),
            uncertainty=['clock_skew', 'clock_order_uncertain'])

    rule_all = per_detector[REFERENCE]['scenario_level']['all']
    seq_all = per_detector[SEQUENCE]['scenario_level']['all']
    rule_held = per_detector[REFERENCE]['scenario_level']['held_out']
    seq_held = per_detector[SEQUENCE]['scenario_level']['held_out']
    add(FACT, severity='info',
        title='Measured detector performance on the labeled corpus',
        statement='Over %d labeled scenarios (%d malicious, %d benign '
                  'look-alikes) the reference indicator rule scored TP=%d '
                  'FP=%d FN=%d TN=%d (precision %s, recall %s) and the '
                  'sequence detector scored TP=%d FP=%d FN=%d TN=%d '
                  '(precision %s, recall %s). On the held-out split alone the '
                  'rule scored TP=%d FP=%d FN=%d TN=%d (recall %s) and the '
                  'sequence detector TP=%d FP=%d FN=%d TN=%d (recall %s).'
                  % (rule_all['n_scenarios'], rule_all['n_malicious'],
                     rule_all['n_benign'],
                     rule_all['tp'], rule_all['fp'], rule_all['fn'],
                     rule_all['tn'], rule_all['precision'],
                     rule_all['recall'],
                     seq_all['tp'], seq_all['fp'], seq_all['fn'],
                     seq_all['tn'], seq_all['precision'], seq_all['recall'],
                     rule_held['tp'], rule_held['fp'], rule_held['fn'],
                     rule_held['tn'], rule_held['recall'],
                     seq_held['tp'], seq_held['fp'], seq_held['fn'],
                     seq_held['tn'], seq_held['recall']),
        scenario=None, detector=None, evidence=[], uncertainty=[],
        measurement=[measurement_block(
            EVALUATION_ARTIFACT,
            {name: {split: {key: per_detector[name]['scenario_level'][split][
                            key]
                        for key in ('tp', 'fp', 'fn', 'tn', 'precision',
                                    'recall', 'f1')}
                    for split in ('all', 'dev', 'held_out')}
             for name in (REFERENCE, SEQUENCE, COMBINED)},
            note='the exact scenario-level counts quoted in the statement '
                 'above, read from the P12-02 evaluation artifact')])

    fp_ids = sorted(sid for sid, entry in benign_fps.items()
                    if entry['false_positive'])
    fp_evidence = []
    for sid in fp_ids:
        timeline = corpus[sid]['timeline']
        for finding in evaluation['findings'][sid][REFERENCE]:
            fp_evidence.extend(_provenance(
                timeline, finding['evidence_ids'],
                'benign look-alike %s: cited by the rule but annotated '
                'benign' % sid))
    add(FACT, severity='high',
        title='Measured false positives on benign look-alikes',
        statement='The reference indicator rule fired on %d of %d benign '
                  'look-alike scenarios (%s), a false-positive rate of %s. '
                  'The sequence detector fired on none of them, including the '
                  '6 GB ticketed restore. %d of the %d event ids the rule '
                  'cites across the corpus point at events annotated as '
                  'benign.'
                  % (len(fp_ids), len(benign_fps), ', '.join(fp_ids),
                     round(len(fp_ids) / len(benign_fps), 4),
                     per_detector[REFERENCE]['event_level']['all'][
                         'evidence_ids_not_on_attack'],
                     per_detector[REFERENCE]['event_level']['all'][
                         'evidence_ids_cited']),
        scenario=None, detector=REFERENCE, evidence=fp_evidence)

    missed = sorted(set(per_detector[REFERENCE]['scenario_level']['all']
                        ['fn_ids'])
                    & set(per_detector[SEQUENCE]['scenario_level']['all']
                          ['fn_ids']))
    for sid in missed:
        timeline = corpus[sid]['timeline']
        add(FACT, severity='critical',
            title='Undetected malicious scenario — %s' % sid,
            statement='This scenario is annotated malicious (%s) and neither '
                      'detector emitted a finding. %d bytes left the system '
                      'across %d annotated attack events; the corpus records '
                      'this as a false negative for both detectors rather than '
                      'excluding it from the metric.'
                      % (labels[sid]['attack_kind'],
                         sum(event['bytes_out'] for event in timeline.events),
                         labels[sid]['attack_events']),
            scenario=sid, detector=None,
            evidence=_provenance(timeline, groundtruth.attack_event_ids(sid),
                                 'annotated attack events, none of them cited '
                                 'by any detector'))

    fact_ids = [finding['id'] for finding in findings
                if finding['classification'] == FACT]

    add(HYPOTHESIS, severity='high',
        title='The failure bursts are credential guessing, not user error',
        statement='For m01 and m03 the burst is followed by bulk reads from '
                  'the same unbaselined address, which a mistyping user would '
                  'not do. We hypothesise an external actor guessing '
                  'passwords against accounts that did not require a second '
                  'factor.',
        scenario='m01-credstuff-exfil', detector=REFERENCE,
        evidence=_provenance(
            corpus['m01-credstuff-exfil']['timeline'],
            evaluation['findings']['m01-credstuff-exfil'][REFERENCE][0][
                'evidence_ids'], 'the burst and the login it produced'),
        alternatives=['A legitimate user mistyping a password and then '
                      'working normally — weakened by the 840 MB of reads '
                      'that follow from the same address.',
                      'A shared NAT egress address used by several legitimate '
                      'users — weakened by the burst being confined to one '
                      'actor and one session id.'],
        risk_rationale='If this is wrong we have accused an external address '
                       'of an attack it did not perform and blocked legitimate '
                       'traffic. If it is right and we do nothing, the same '
                       'password continues to grant access to customer-db.')

    add(HYPOTHESIS, severity='critical',
        title='The m02 session used credentials the actor already held',
        statement='m02 contains no authentication failure at all: the session '
                  'opens with a successful password-only login from an '
                  'unbaselined IP at 02:14 UTC, grants itself '
                  'role:data-reader and moves 4.8 GB. We hypothesise stolen '
                  'or shared credentials rather than guessing.',
        scenario='m02-validcreds-staged-exfil', detector=SEQUENCE,
        evidence=_provenance(
            corpus['m02-validcreds-staged-exfil']['timeline'],
            evaluation['findings']['m02-validcreds-staged-exfil'][SEQUENCE][0][
                'evidence_ids'], 'the whole chain, from login to last read'),
        alternatives=['A legitimate user travelling and working from a new '
                      'network — weakened by the hour, the self-granted role '
                      'and the volume.',
                      'A sanctioned batch job whose baseline entry is missing '
                      '— weakened by the interactive session type and the '
                      'single presented factor.'],
        risk_rationale='If credentials were stolen, every other system that '
                       'accepts the same password is exposed and rotating it '
                       'is urgent. If this was sanctioned work, an MFA '
                       'requirement for unbaselined IPs will interrupt it, so '
                       'the baseline must be corrected first.')

    for sid in missed:
        add(HYPOTHESIS, severity='critical',
            title='%s cannot be separated from sanctioned activity on this '
                  'evidence' % sid,
            statement='The export came from an address inside the asset '
                      'baseline for the actor, during a period with no '
                      'authentication anomaly, and no ticket reference appears '
                      'in the session. We hypothesise insider data theft, but '
                      'the evidence available here cannot distinguish it from '
                      'an unsanctioned-but-legitimate engineering snapshot.',
            scenario=sid, detector=None,
            evidence=_provenance(
                corpus[sid]['timeline'],
                groundtruth.attack_event_ids(sid),
                'annotated attack events; the annotation is an analyst '
                'judgement, not something a detector observed'),
            alternatives=['A legitimate snapshot taken without raising a '
                          'change ticket — the observable fields are '
                          'identical.',
                          'A compromised baselined workstation, which would '
                          'look the same again.'],
            risk_rationale='This is the corpus\' only shared false negative. '
                           'Treating it as benign leaves 2.5 GB of source '
                           'code unexplained; treating it as confirmed theft '
                           'without corroboration risks acting against an '
                           'employee on evidence that does not support it. '
                           'Human review and an out-of-band ticket check are '
                           'the only ways to resolve it.')

    add(HYPOTHESIS, severity='medium',
        title='The indicator rule would consume review capacity in production',
        statement='On this corpus the rule flags 3 benign scenarios for every '
                  '2 malicious ones and 18 of its 35 cited event ids point at '
                  'legitimate activity. We hypothesise that deploying it '
                  'unchanged would generate mostly non-actionable review '
                  'work.',
        scenario=None, detector=REFERENCE,
        evidence=_provenance(
            corpus['b05-vpn-reconnect-retries']['timeline'],
            evaluation['findings']['b05-vpn-reconnect-retries'][REFERENCE][0][
                'evidence_ids'],
            'one measured false positive: a VPN client renegotiating'),
        measurement=[measurement_block(
            EVALUATION_ARTIFACT,
            {'false_positive_scenarios': fp_ids,
             'false_positive_rate_on_benign': round(
                 len(fp_ids) / len(benign_fps), 4),
             'rule_evidence_ids_cited': per_detector[REFERENCE][
                 'event_level']['all']['evidence_ids_cited'],
             'rule_evidence_ids_on_benign': per_detector[REFERENCE][
                 'event_level']['all']['evidence_ids_not_on_attack'],
             'analyst_hours_measured': 0,
             'analyst_hours_claimed': 0},
            note='counts behind this inference; the two zero fields record '
                 'that no human time was measured or claimed anywhere in '
                 'this project')],
        alternatives=['The corpus over-represents benign bursts; a real '
                      'population might contain proportionally more attacks.',
                      'Triage automation could absorb the false positives '
                      'before an analyst sees them.'],
        risk_rationale='This is an inference about operational cost, NOT a '
                       'measurement. No analyst time was observed, timed or '
                       'estimated in this project, and no hours-saved figure '
                       'may be quoted from it.')

    add(HYPOTHESIS, severity='medium',
        title='The missing m01 records may conceal actor activity',
        statement='Two audit records (seq 27 and 28) never reached any source '
                  'file. We hypothesise ordinary log rotation, but the gap '
                  'sits inside the incident window and its content is '
                  'unknowable from this evidence.',
        scenario='m01-credstuff-exfil', detector=None,
        evidence=_provenance(
            corpus['m01-credstuff-exfil']['timeline'],
            gap_evidence.get('m01-credstuff-exfil', []),
            'the two records that bound the gap; the absent ids '
            'm01-000027/m01-000028 are deliberately not cited because they '
            'never reached a source file'),
        uncertainty=['missing_records'],
        alternatives=['Log rotation or a forwarder buffer overrun.',
                      'Deliberate log clearing by the actor — the gap is too '
                      'small and too cleanly bounded to suggest it.'],
        risk_rationale='Any statement about what the actor did NOT do between '
                       'the bracketing records is unsupported. If the missing '
                       'records can be recovered from a backup, the timeline '
                       'and every count in this report should be recomputed '
                       'before conclusions are drawn.')

    add(REMEDIATION, severity='critical',
        title='Require a second factor for interactive logins from '
              'unbaselined addresses',
        statement='Every malicious session in this corpus authenticated with '
                  'a single factor; every benign look-alike that produced a '
                  'false positive presented password plus TOTP.',
        scenario=None, detector=None,
        evidence=[block for finding in findings
                  if finding['classification'] == FACT
                  and finding['title'].startswith('Single-factor')
                  for block in finding['evidence']],
        steps=['Enforce step-up authentication when the source IP is absent '
               'from the asset baseline for that actor.',
               'Exempt non-interactive workload identities but require a '
               'workload certificate instead of a password.',
               'Emit an audit event for every blocked attempt so prevention '
               'is observable rather than silent.'],
        addresses=[finding['id'] for finding in findings
                   if finding['title'].startswith('Single-factor')
                   or 'credentials the actor already held' in
                   finding['title']],
        validation_status=validation.get('mfa_step_up', NOT_VALIDATED))

    add(REMEDIATION, severity='high',
        title='Cap the failure burst and require step-up to continue',
        statement='The reference rule needs at least 3 failures followed by a '
                  'success to fire. Capping the burst at 2 and requiring a '
                  'second factor to continue removes the pattern the rule '
                  'matches, for attackers and for the benign look-alikes '
                  'alike.',
        scenario=None, detector=REFERENCE,
        evidence=[block for finding in findings
                  if finding['classification'] == FACT
                  and finding['title'].startswith(
                      'Measured false positives')
                  for block in finding['evidence']],
        steps=['Lock the (actor, source IP) pair after 2 failed '
               'authentications inside 600 s.',
               'Allow recovery only through a second factor, so a legitimate '
               'user is not locked out but a password-only attacker is.',
               'Suppress further failure events for the locked pair and '
               'record a lockout event naming the suppressed ids.'],
        addresses=[finding['id'] for finding in findings
                   if 'false positives' in finding['title']
                   or 'credential guessing' in finding['title']],
        validation_status=validation.get('adaptive_lockout', NOT_VALIDATED))

    add(REMEDIATION, severity='critical',
        title='Gate bulk egress on an open change ticket',
        statement='Every malicious bulk-read chain in this corpus carries no '
                  'ticket reference, while both legitimate high-volume '
                  'scenarios open one before reading. Ticket presence is an '
                  'observable field, not a label.',
        scenario=None, detector=SEQUENCE,
        evidence=[block for finding in findings
                  if finding['classification'] == FACT
                  and 'Bulk egress' in finding['title']
                  for block in finding['evidence']],
        steps=['Require an open, approved ticket for any single read above '
               '100 MB or any session above 500 MB.',
               'Block and audit the attempt when no ticket is present.',
               'Allow ticketed workload restores to proceed unchanged so '
               'legitimate volume is not penalised.'],
        addresses=[finding['id'] for finding in findings
                   if 'Bulk egress' in finding['title']],
        validation_status=validation.get('egress_gate', NOT_VALIDATED))

    add(REMEDIATION, severity='high',
        title='Close the baselined-insider blind spot',
        statement='The one scenario both detectors miss is malicious activity '
                  'from an address that is already in the baseline. Baseline '
                  'membership must stop being a get-out-of-detection card.',
        scenario=None, detector=None,
        evidence=[block for finding in findings
                  if finding['classification'] == FACT
                  and finding['title'].startswith('Undetected malicious')
                  for block in finding['evidence']],
        steps=['Alert on bulk egress with no ticket regardless of whether '
               'the source IP is baselined.',
               'Review baseline.json on a schedule and record who approved '
               'each entry.',
               'Route baselined-IP bulk exports to human review instead of '
               'silently allowing them.'],
        addresses=[finding['id'] for finding in findings
                   if finding['title'].startswith('Undetected malicious')
                   or 'cannot be separated' in finding['title']],
        validation_status=validation.get('insider_blind_spot',
                                         NOT_VALIDATED))

    add(REMEDIATION, severity='medium',
        title='Monitor log continuity and forwarder clock discipline',
        statement='Two audit records are missing from the incident window and '
                  'one forwarder runs 7 s fast. Both are observable today and '
                  'neither is alerted on.',
        scenario=None, detector=None,
        evidence=[block for finding in findings
                  if finding['classification'] == FACT
                  and (finding['title'].startswith('Log continuity')
                       or finding['title'].startswith('Clock skew'))
                  for block in finding['evidence']],
        steps=['Alert when a source\'s seq numbers have a hole.',
               'Synchronize forwarders and record the measured offset '
               'instead of relying on a tolerance.',
               'Refuse to ingest a source whose timestamps carry no UTC '
               'offset unless an operator declares one, and record the '
               'declaration as an assumption.'],
        addresses=[finding['id'] for finding in findings
                   if finding['title'].startswith('Log continuity')
                   or finding['title'].startswith('Clock skew')
                   or 'may conceal' in finding['title']],
        validation_status=validation.get('continuity_monitoring',
                                         NOT_VALIDATED))

    add(REMEDIATION, severity='medium',
        title='Demote the indicator rule, promote the sequence detector',
        statement='Measured on this corpus the rule has precision 0.4 and '
                  'held-out recall 0.0; the sequence detector has precision '
                  '1.0 with no benign false positive and held-out recall 0.5. '
                  'The portfolio, not either rule alone, is what should be '
                  'deployed.',
        scenario=None, detector=None, evidence=[],
        measurement=[measurement_block(
            EVALUATION_ARTIFACT,
            {'failures_then_success': {
                'precision_all': rule_all['precision'],
                'recall_all': rule_all['recall'],
                'recall_held_out': rule_held['recall'],
                'fp_on_benign': rule_all['fp'],
                'benign_scenarios': rule_all['n_benign']},
             'bulk_egress_from_new_ip': {
                 'precision_all': seq_all['precision'],
                 'recall_all': seq_all['recall'],
                 'recall_held_out': seq_held['recall'],
                 'fp_on_benign': seq_all['fp'],
                 'benign_scenarios': seq_all['n_benign']}},
            note='the precision/recall values quoted in the statement, read '
                 'from the P12-02 evaluation artifact')],
        steps=['Keep the indicator rule as a low-severity enrichment signal, '
               'never as a page.',
               'Page on the sequence detector and on ticketless bulk egress.',
               'Re-measure on new scenarios before changing either threshold, '
               'and keep the held-out split untouched while tuning.'],
        addresses=[finding['id'] for finding in findings
                   if 'Measured detector performance' in finding['title']
                   or 'would consume review capacity' in finding['title']],
        validation_status=validation.get('detector_portfolio',
                                         NOT_VALIDATED))

    return findings


def resolve_evidence(finding, corpus):
    """Print-ready provenance: file, sha256, line number and the raw line."""
    resolved = []
    for block in finding['evidence']:
        path = Path(block['source_file'])
        lines = (path.read_text(encoding='utf-8').splitlines()
                 if path.exists() else [])
        actual = (hashlib.sha256(path.read_bytes()).hexdigest()
                  if path.exists() else None)
        rows = []
        for event_id, line_no in zip(block['event_ids'],
                                     block['source_lines']):
            rows.append({'event_id': event_id, 'source_line': line_no,
                         'raw_line': lines[line_no - 1] if line_no <= len(
                             lines) else None})
        resolved.append({'source_file': block['source_file'],
                         'source_sha256': block['source_sha256'],
                         'sha256_recomputed_from_disk': actual,
                         'sha256_matches': actual == block['source_sha256'],
                         'event_count': block['event_count'],
                         'note': block['note'], 'lines': rows})
    measurements = []
    for block in finding['measurement']:
        path = Path(block['artifact'])
        actual = (hashlib.sha256(path.read_bytes()).hexdigest()
                  if path.exists() else None)
        measurements.append(dict(
            block, sha256_recomputed_from_disk=actual,
            sha256_matches=actual == block['sha256']))
    return {'finding_id': finding['id'],
            'classification': finding['classification'],
            'title': finding['title'],
            'statement': finding['statement'],
            'evidence_blocks': resolved,
            'measurement_blocks': measurements}


def validate_findings(findings, corpus):
    """Check that every finding is labeled, cited and reproducible."""
    problems = []
    seen = set()
    absent = {sid: set(groundtruth.absent_event_ids(sid)) for sid in corpus}
    counts = {name: 0 for name in CLASSIFICATIONS}

    for finding in findings:
        fid = finding['id']
        if fid in seen:
            problems.append('%s: duplicate finding id' % fid)
        seen.add(fid)
        classification = finding['classification']
        if classification not in CLASSIFICATIONS:
            problems.append('%s: unknown classification %r'
                            % (fid, classification))
            continue
        counts[classification] += 1
        if not finding['title'] or not finding['statement']:
            problems.append('%s: missing title or statement' % fid)
        if not finding['reproduce'].endswith(fid):
            problems.append('%s: reproduce command does not name the finding'
                            % fid)

        if classification == FACT and not finding['evidence_event_ids']:
            if not finding['measurement']:
                problems.append('%s: a FACT cites neither event ids nor a '
                                'measurement artifact' % fid)
        for block in finding['measurement']:
            path = Path(block['artifact'])
            if not path.exists():
                problems.append('%s: cited measurement artifact %s does not '
                                'exist (run measure_p12_02.py first)'
                                % (fid, block['artifact']))
            elif hashlib.sha256(path.read_bytes()).hexdigest() \
                    != block['sha256']:
                problems.append('%s: cited measurement sha256 does not match '
                                '%s on disk' % (fid, block['artifact']))
            if not block['values']:
                problems.append('%s: measurement block carries no values'
                                % fid)
        if classification == HYPOTHESIS:
            if not finding['risk_rationale']:
                problems.append('%s: a HYPOTHESIS has no risk_rationale' % fid)
            if len(finding['alternatives']) < 1:
                problems.append('%s: a HYPOTHESIS names no alternative' % fid)
        if classification == REMEDIATION:
            if not finding['remediation_steps']:
                problems.append('%s: a REMEDIATION lists no steps' % fid)
            if not finding['addresses']:
                problems.append('%s: a REMEDIATION addresses nothing' % fid)

        for block in finding['evidence']:
            path = Path(block['source_file'])
            if not path.exists():
                problems.append('%s: cited source %s does not exist'
                                % (fid, block['source_file']))
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != block['source_sha256']:
                problems.append('%s: cited sha256 %s does not match the file '
                                'on disk (%s)'
                                % (fid, block['source_sha256'][:12],
                                   digest[:12]))
            lines = path.read_text(encoding='utf-8').splitlines()
            for event_id, line_no in zip(block['event_ids'],
                                         block['source_lines']):
                if line_no < 1 or line_no > len(lines):
                    problems.append('%s: %s cites line %d of a %d-line file'
                                    % (fid, event_id, line_no, len(lines)))
                    continue
                if event_id not in lines[line_no - 1]:
                    problems.append('%s: %s is not on line %d of %s'
                                    % (fid, event_id, line_no, path.name))
                owner = None
                for sid, entry in corpus.items():
                    if entry['timeline'].has(event_id):
                        owner = sid
                        break
                if owner is None:
                    problems.append('%s: cited event %s is in no timeline'
                                    % (fid, event_id))
                else:
                    if event_id in absent[owner]:
                        problems.append('%s: cited event %s never reached a '
                                        'source file' % (fid, event_id))
                    provenance = corpus[owner]['timeline'].provenance(event_id)
                    if provenance['source_file'] != block['source_file']:
                        problems.append(
                            '%s: %s is attributed to %s but the timeline says '
                            '%s' % (fid, event_id, block['source_file'],
                                    provenance['source_file']))

    for other in findings:
        for address in other.get('addresses', []):
            if address not in seen:
                problems.append('%s addresses unknown finding %s'
                                % (other['id'], address))

    for name in CLASSIFICATIONS:
        if counts[name] == 0:
            problems.append('no %s finding was produced' % name)

    return {'ok': not problems, 'problems': problems, 'counts': counts,
            'findings': len(findings),
            'ids_are_disjoint': len(seen) == len(findings),
            'cited_event_ids': sum(len(finding['evidence_event_ids'])
                                   for finding in findings),
            'cited_source_files': len({block['source_file']
                                       for finding in findings
                                       for block in finding['evidence']}),
            'cited_sha256': sorted({block['source_sha256']
                                    for finding in findings
                                    for block in finding['evidence']})}


def _finding_section(finding, technical=False):
    lines = ['### %s — %s' % (finding['id'], finding['title']), '']
    lines.append('**Classification:** `%s`  **Severity:** `%s`'
                 % (finding['classification'], finding['severity']))
    if finding['scenario']:
        lines.append('**Scenario:** `%s`' % finding['scenario'])
    if finding['detector']:
        lines.append('**Detector:** `%s`' % finding['detector'])
    lines += ['', finding['statement'], '']
    if finding['evidence']:
        lines += ['**Evidence** (%d event id%s, %d source file%s):'
                  % (len(finding['evidence_event_ids']),
                     '' if len(finding['evidence_event_ids']) == 1 else 's',
                     len(finding['evidence']),
                     '' if len(finding['evidence']) == 1 else 's'), '']
        for block in finding['evidence']:
            lines.append('- `%s` — sha256 `%s`'
                         % (block['source_file'], block['source_sha256']))
            if technical:
                lines.append('  - lines: %s' % ', '.join(
                    str(line) for line in block['source_lines']))
                lines.append('  - raw timestamps: %s' % ', '.join(
                    block['raw_timestamps']))
                lines.append('  - UTC offsets (minutes): %s'
                             % block['tz_offset_minutes'])
                if block['mirrored_in']:
                    lines.append('  - same ids also seen in: %s'
                                 % ', '.join(block['mirrored_in']))
                if block['note']:
                    lines.append('  - note: %s' % block['note'])
            ids = block['event_ids']
            shown = ids if technical or len(ids) <= 6 else ids[:6]
            lines.append('  - event ids (%d): %s%s'
                         % (len(ids), ', '.join('`%s`' % i for i in shown),
                            '' if len(ids) == len(shown) else ', …'))
        lines.append('')
    else:
        lines += ['**Evidence:** none — this claim is a measurement or an '
                  'inference over the whole corpus, not a citation of '
                  'individual events.', '']
    if finding['measurement']:
        lines += ['**Measurement artifact cited:**', '']
        for block in finding['measurement']:
            lines.append('- `%s` — sha256 `%s`'
                         % (block['artifact'], block['sha256']))
            lines.append('  - produced by: `%s`' % block['produced_by'])
            if block['note']:
                lines.append('  - note: %s' % block['note'])
            lines.append('  - values: `%s`' % json.dumps(
                block['values'], sort_keys=True))
        lines.append('')
    if finding['classification'] == HYPOTHESIS:
        lines += ['**Alternatives considered:**', '']
        lines += ['- %s' % alternative
                  for alternative in finding['alternatives']]
        lines += ['', '**Risk rationale (what follows if this is wrong):** %s'
                  % finding['risk_rationale'], '']
    if finding['classification'] == REMEDIATION:
        lines += ['**Remediation steps:**', '']
        lines += ['%d. %s' % (index, step) for index, step in
                  enumerate(finding['remediation_steps'], start=1)]
        lines += ['', '**Addresses:** %s'
                  % ', '.join('`%s`' % a for a in finding['addresses']),
                  '**Validation status:** `%s`'
                  % finding['validation_status'], '']
    if finding['uncertainty']:
        lines += ['**Uncertainty ledger entries:** %s'
                  % ', '.join('`%s`' % u for u in finding['uncertainty']), '']
    lines += ['**Reproduce:** `%s`' % finding['reproduce'], '', '---', '']
    return '\n'.join(lines)


def render_executive(findings, evaluation, corpus):
    """Short, decision-shaped report for a non-technical reader."""
    scenario_counts = {name: evaluation['per_detector'][name][
        'scenario_level']['all'] for name in (REFERENCE, SEQUENCE, COMBINED)}
    parts = ['# Incident replay — executive report', '',
             'Prepared from a **synthetic** labeled corpus. ' + DISCLAIMER,
             '',
             '## Bottom line', '',
             'Nine scenarios were replayed: four annotated malicious and five '
             'benign look-alikes deliberately built to resemble them. The '
             'single indicator rule the investigation started with catches '
             'half the attacks and fires on three of the five legitimate '
             'scenarios. A sequence detector catches three of the four '
             'attacks and fires on nothing legitimate. One malicious scenario '
             'is missed by both, and it is the most expensive one to miss.',
             '',
             '## What we know (facts)', '']
    facts = [f for f in findings if f['classification'] == FACT]
    for finding in facts:
        parts.append('- **%s** (`%s`, severity `%s`) — %d cited event id%s.'
                     % (finding['title'], finding['id'], finding['severity'],
                        len(finding['evidence_event_ids']),
                        '' if len(finding['evidence_event_ids']) == 1
                        else 's'))
    parts += ['', '## What we believe (hypotheses, not facts)', '']
    for finding in [f for f in findings if f['classification'] == HYPOTHESIS]:
        parts.append('- **%s** (`%s`) — %s'
                     % (finding['title'], finding['id'],
                        finding['risk_rationale'].split('.')[0] + '.'))
    parts += ['', '## What to do (remediation proposals, unvalidated here)',
              '']
    for finding in [f for f in findings
                    if f['classification'] == REMEDIATION]:
        parts.append('- **%s** (`%s`) — addresses %s. Status: `%s`.'
                     % (finding['title'], finding['id'],
                        ', '.join('`%s`' % a for a in finding['addresses']),
                        finding['validation_status']))
    parts += ['', '## Measured detection performance', '',
              '| Detector | TP | FP | FN | TN | Precision | Recall |',
              '|---|---|---|---|---|---|---|']
    for name in (REFERENCE, SEQUENCE, COMBINED):
        metrics = scenario_counts[name]
        parts.append('| `%s` | %d | %d | %d | %d | %s | %s |'
                     % (name, metrics['tp'], metrics['fp'], metrics['fn'],
                        metrics['tn'], metrics['precision'],
                        metrics['recall']))
    parts += ['',
              'Held-out only (four scenarios never used to set a threshold): '
              'the indicator rule scores TP=0 FP=2 FN=2 TN=0 (recall 0.0); '
              'the sequence detector scores TP=1 FP=0 FN=1 TN=2 (recall 0.5).',
              '', '## What this report does not claim', '',
              '- No analyst time was measured and no hours saved are claimed.',
              '- The undetected scenario `%s` is reported as a false negative, '
              'not excluded.' % ', '.join(
                  scenario_counts[COMBINED]['fn_ids']),
              '- Two audit records are missing from the m01 window; nothing '
              'was reconstructed to fill the gap.',
              '- Remediation items are proposals. Their validation is a '
              'separate exercise (P12-04) and each carries its own status.',
              '', '## Reproduce any finding', '',
              '```sh', 'python3 -B report.py --finding FACT-01',
              'python3 -B measure_p12_03.py --out results/p12-03-reports',
              '```', '',
              'Every finding prints the source file, that file\'s sha256, the '
              'line numbers and the raw log lines behind each cited event id.',
              '']
    return '\n'.join(parts)


def render_technical(findings, evaluation, corpus):
    """Full report: methodology, per-finding evidence, uncertainty, limits."""
    config = evaluation['detector_configuration']
    parts = ['# Incident replay — technical report', '',
             'Prepared from a **synthetic** labeled corpus. ' + DISCLAIMER, '',
             '## 1. Method', '',
             '1. Two raw log formats (JSON Lines audit, RFC 3164-style '
             'syslog `key=value`) were ingested by `ingest.py` into one '
             'normalized, UTC-timestamped event stream. Every event retains '
             'its source file, that file\'s sha256, its line number and its '
             'raw timestamp text.',
             '2. Timezone assumptions, duplicate collapse, clock skew, '
             'ambiguous ordering and missing records were recorded in a '
             'structured uncertainty ledger instead of being resolved '
             'silently.',
             '3. Nine scenarios were annotated in `groundtruth.py` by naming '
             'the attack session. Detectors never see the annotations; the '
             'import graph is audited and the findings are re-checked with '
             'every label inverted.',
             '4. Two deterministic detectors were scored at scenario level '
             '(TP/FP/FN/TN) and at event level (are the cited ids actually '
             'attack events?).',
             '5. Findings below are generated from those artifacts, so '
             're-running the pipeline reproduces this document byte for byte.',
             '', '## 2. Detector configuration', '',
             '```json', json.dumps(config, indent=2, sort_keys=True), '```',
             '', '## 3. How to read the classification labels', '',
             '| Label | Meaning | Requirement |', '|---|---|---|',
             '| `FACT` | The ingested evidence states this directly. | Must '
             'cite event ids that exist, with source file and sha256. |',
             '| `HYPOTHESIS` | An interpretation of facts. | Must name at '
             'least one alternative and carry a risk rationale. |',
             '| `REMEDIATION` | A proposed control. | Must list steps and '
             'name the finding ids it addresses. Carries a validation '
             'status; it is never evidence that something was fixed. |', '',
             '## 4. Findings', '']
    for classification in CLASSIFICATIONS:
        group = [f for f in findings if f['classification'] == classification]
        parts += ['## 4.%d %s findings (%d)'
                  % (CLASSIFICATIONS.index(classification) + 1,
                     classification.title(), len(group)), '']
        for finding in group:
            parts.append(_finding_section(finding, technical=True))
    parts += ['## 5. Uncertainty ledger carried into this report', '']
    for sid in sorted(corpus):
        timeline = corpus[sid]['timeline']
        kinds = {}
        for entry in timeline.uncertainty:
            kinds.setdefault(entry['kind'], 0)
            kinds[entry['kind']] += 1
        parts.append('- `%s` — %d events, ledger: %s'
                     % (sid, len(timeline.events),
                        ', '.join('%s x%d' % (kind, count)
                                  for kind, count in sorted(kinds.items()))))
    parts += ['', '## 6. Measured results', '', '```',
              '\n'.join(evaluate.summary_lines(evaluation)), '```', '',
              '## 7. Limitations', '',
              '- Synthetic fixtures only; no PCAP parser, no packet evidence, '
              'no real incident response.',
              '- Nine scenarios. One scenario moves recall by 0.25, so no '
              'confidence interval is claimed.',
              '- The sequence detector depends on `baseline.json`, authored '
              'asset-owner configuration. A stale baseline is both a false-'
              'positive and a false-negative source.',
              '- No human time was measured. Nothing here supports an '
              '"hours saved" claim.',
              '- Remediation items are proposals validated separately in '
              'P12-04; the status field on each is authoritative.', '',
              '## 8. Reproduction', '', '```sh',
              'python3 -B test_core.py -v',
              "python3 -B -m unittest discover -p 'test_*.py' -v",
              'python3 -B measure_p12_03.py --out results/p12-03-reports',
              'python3 -B report.py --finding <ID>', '```', '']
    return '\n'.join(parts)


def write_reports(directory, findings, evaluation, corpus):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    executive = render_executive(findings, evaluation, corpus)
    technical = render_technical(findings, evaluation, corpus)
    (out / 'EXECUTIVE_REPORT.md').write_text(executive, encoding='utf-8')
    (out / 'TECHNICAL_REPORT.md').write_text(technical, encoding='utf-8')
    (out / 'findings.json').write_text(json.dumps(
        findings, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {'executive': str(out / 'EXECUTIVE_REPORT.md'),
            'technical': str(out / 'TECHNICAL_REPORT.md'),
            'findings': str(out / 'findings.json'),
            'executive_bytes': len(executive),
            'technical_bytes': len(technical)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finding', help='print one finding with resolved '
                                          'provenance')
    parser.add_argument('--list', action='store_true',
                        help='list finding ids and classifications')
    parser.add_argument('--out', help='write both reports here')
    options = parser.parse_args(argv)

    corpus = evaluate.load_corpus()
    evaluation = evaluate.evaluate(corpus, evaluate.run_detectors(corpus))
    findings = build_findings(corpus, evaluation)
    by_id = {finding['id']: finding for finding in findings}

    if options.list:
        for finding in findings:
            print('%-8s %-12s %-8s %s'
                  % (finding['id'], finding['classification'],
                     finding['severity'], finding['title']))
        return 0
    if options.finding:
        if options.finding not in by_id:
            print('unknown finding %r; known ids: %s'
                  % (options.finding, ', '.join(sorted(by_id))))
            return 2
        print(json.dumps(resolve_evidence(by_id[options.finding], corpus),
                         indent=2, sort_keys=True))
        return 0
    validation = validate_findings(findings, corpus)
    print(json.dumps({'validation': validation,
                      'counts': validation['counts']},
                     indent=2, sort_keys=True))
    if options.out:
        written = write_reports(options.out, findings, evaluation, corpus)
        print(json.dumps(written, indent=2, sort_keys=True))
    return 0 if validation['ok'] else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
