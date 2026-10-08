"""Deterministic detectors for IncidentReplay (P12-02).

Two detectors, deliberately different in kind, are scored against the
annotations in `groundtruth.py`:

* ``failures_then_success`` — the **reference indicator rule**, taken
  unchanged from `project.analyze`. Events are projected onto the reference
  kernel's exact five-key contract (`ingest.to_reference_events`), so the
  reference file is never edited to make a metric look better. It matches a
  single indicator: >= `minimum` authentication failures for one
  `(user, ip)` inside `window` seconds, followed by a success.
* ``bulk_egress_from_new_ip`` — a **sequence detector**. It requires an
  ordered chain: a success from an IP that is *not* in the asset baseline for
  that actor, followed inside `window_seconds` by at least `min_objects`
  data-plane reads totalling at least `egress_threshold_bytes`.

Neither detector is given a label. Their only inputs are the normalized event
stream and the asset-owner baseline config; `test_evaluate.py` asserts that
neither this module nor `ingest.py` imports `groundtruth`.

Both emit one finding shape so the scorer and the report generator can treat
them uniformly, and every finding carries the exact `evidence_ids` that
support it — a finding with no evidence is not emitted.
"""
from ingest import to_reference_events
from project import analyze

REFERENCE_RULE = 'failures_then_success'
SEQUENCE_RULE = 'bulk_egress_from_new_ip'

DATA_PLANE_ACTIONS = ('download', 'export')

REFERENCE_WINDOW_SECONDS = 300
REFERENCE_MINIMUM_FAILURES = 3
SEQUENCE_WINDOW_SECONDS = 3600
SEQUENCE_EGRESS_THRESHOLD_BYTES = 500_000_000
SEQUENCE_MIN_OBJECTS = 5
CRITICAL_EGRESS_BYTES = 1_000_000_000


def known_ips(baseline, user):
    """Baselined source IPs for an actor; unknown actors have none."""
    return list((baseline or {}).get('users', {}).get(user, {})
                .get('known_ips', []))


def _finding(detector, scenario, user, ip, evidence, severity, confidence,
             detail):
    """Build one finding; ``evidence`` is the list of supporting events."""
    if not evidence:
        raise ValueError('a finding with no supporting evidence is not '
                         'emitted by this module')
    return {'detector': detector, 'rule': detector, 'scenario': scenario,
            'user': user, 'ip': ip, 'severity': severity,
            'confidence': confidence,
            'evidence_ids': [event['id'] for event in evidence],
            'first_event_at': min(event['at'] for event in evidence),
            'last_event_at': max(event['at'] for event in evidence),
            'detail': detail}


def run_reference(events, scenario, baseline=None,
                  window=REFERENCE_WINDOW_SECONDS,
                  minimum=REFERENCE_MINIMUM_FAILURES):
    """The untouched reference indicator rule, per scenario.

    ``baseline`` is accepted and ignored so every detector in the registry
    shares one call signature; the reference rule uses no configuration
    beyond its own window and threshold.
    """
    projected = to_reference_events(events)
    if not projected:
        return []
    result = analyze(projected, window=window, minimum=minimum)
    by_id = {event['id']: event for event in events}
    findings = []
    for raw in result['findings']:
        evidence = [by_id[event_id] for event_id in raw['evidence_ids']]
        failures = sum(1 for event in evidence
                       if event['kind'] == 'failure')
        span = evidence[-1]['at_epoch'] - evidence[0]['at_epoch']
        findings.append(_finding(
            REFERENCE_RULE, scenario, raw['user'], raw['ip'], evidence,
            raw['severity'], raw['confidence'],
            {'failures': failures, 'successes': len(evidence) - failures,
             'window_seconds': window, 'minimum_failures': minimum,
             'burst_span_seconds': round(span, 3),
             'bytes_out_total': sum(event['bytes_out']
                                    for event in evidence),
             'reference_input_sha256': result['input_sha256'],
             'excluded_data_plane_events':
                 len(events) - len(projected)}))
    return findings


def run_bulk_egress(events, scenario, baseline,
                    window_seconds=SEQUENCE_WINDOW_SECONDS,
                    egress_threshold_bytes=SEQUENCE_EGRESS_THRESHOLD_BYTES,
                    min_objects=SEQUENCE_MIN_OBJECTS):
    """Sequence detector: unbaselined login, then a bulk read chain."""
    ordered = sorted(events, key=lambda event: (event['at_epoch'],
                                                event['id']))
    findings = []
    for index, event in enumerate(ordered):
        if event['kind'] != 'success':
            continue
        user, ip = event['user'], event['ip']
        if ip in known_ips(baseline, user):
            continue
        horizon = event['at_epoch'] + window_seconds
        chain = [other for other in ordered[index:]
                 if other['user'] == user and other['ip'] == ip
                 and other['at_epoch'] <= horizon]
        reads = [other for other in chain
                 if other['action'] in DATA_PLANE_ACTIONS]
        total = sum(other['bytes_out'] for other in reads)
        if len(reads) < min_objects or total < egress_threshold_bytes:
            continue
        severity = ('critical' if total >= CRITICAL_EGRESS_BYTES else 'high')
        findings.append(_finding(
            SEQUENCE_RULE, scenario, user, ip, chain, severity,
            'sequence: unbaselined source IP, then %d bulk reads totalling '
            '%d bytes inside %ds; a legitimate first login from a new device '
            'would look identical' % (len(reads), total, window_seconds),
            {'login_event_id': event['id'],
             'auth_factors': list(event['auth_factors']),
             'baseline_known_ips': known_ips(baseline, user),
             'ip_in_baseline': False,
             'data_plane_objects': len(reads),
             'bytes_out_total': total,
             'window_seconds': window_seconds,
             'egress_threshold_bytes': egress_threshold_bytes,
             'min_objects': min_objects,
             'chain_span_seconds': round(
                 chain[-1]['at_epoch'] - event['at_epoch'], 3),
             'ticket_refs': sorted({other['ticket_ref']
                                    for other in chain
                                    if other['ticket_ref']})}))
    return findings


DETECTORS = {REFERENCE_RULE: run_reference, SEQUENCE_RULE: run_bulk_egress}

DETECTOR_KIND = {REFERENCE_RULE: 'indicator', SEQUENCE_RULE: 'sequence'}

DETECTOR_DESCRIPTIONS = {
    REFERENCE_RULE: 'reference indicator rule from project.analyze: '
                    '>=%d auth failures for one (user, ip) inside %ds, '
                    'followed by a success'
                    % (REFERENCE_MINIMUM_FAILURES, REFERENCE_WINDOW_SECONDS),
    SEQUENCE_RULE: 'sequence detector: an auth success from an IP absent '
                   'from the asset baseline for that actor, followed inside '
                   '%ds by >=%d data-plane reads totalling >=%d bytes'
                   % (SEQUENCE_WINDOW_SECONDS, SEQUENCE_MIN_OBJECTS,
                      SEQUENCE_EGRESS_THRESHOLD_BYTES),
}


def detector_names():
    return sorted(DETECTORS)


def run_detector(name, events, scenario, baseline):
    if name not in DETECTORS:
        raise KeyError('unknown detector %r' % (name,))
    return DETECTORS[name](events, scenario, baseline)


def run_all(events, scenario, baseline, names=None):
    """``{detector_name: [finding, ...]}`` for one scenario."""
    names = detector_names() if names is None else list(names)
    return {name: run_detector(name, events, scenario, baseline)
            for name in names}


def configuration():
    """The exact detector configuration these results were produced with."""
    return {'reference_window_seconds': REFERENCE_WINDOW_SECONDS,
            'reference_minimum_failures': REFERENCE_MINIMUM_FAILURES,
            'sequence_window_seconds': SEQUENCE_WINDOW_SECONDS,
            'sequence_egress_threshold_bytes': SEQUENCE_EGRESS_THRESHOLD_BYTES,
            'sequence_min_objects': SEQUENCE_MIN_OBJECTS,
            'critical_egress_bytes': CRITICAL_EGRESS_BYTES,
            'data_plane_actions': list(DATA_PLANE_ACTIONS),
            'detectors': {name: DETECTOR_DESCRIPTIONS[name]
                          for name in detector_names()},
            'detector_kind': dict(DETECTOR_KIND)}


def flagged(findings_by_scenario, name):
    """Scenario ids on which one detector emitted at least one finding."""
    return sorted(sid for sid, per_detector in findings_by_scenario.items()
                  if per_detector.get(name))


def union_flagged(findings_by_scenario, names=None):
    """Scenario ids flagged by *any* detector (the combined policy)."""
    names = detector_names() if names is None else list(names)
    return sorted(sid for sid, per_detector in findings_by_scenario.items()
                  if any(per_detector.get(name) for name in names))
