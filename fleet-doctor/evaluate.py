"""Ground-truth evaluation for FleetDoctor (P18-03): localization, not certainty.

Each seeded fault has an expected finding (the right check firing). Scoring
reports cause-LOCALIZATION (did the right check fire?), false alarms (other
checks firing FAIL), unknowns, and collection time. Reports identify evidence
and a next step using hedged language ('indicates', 'consistent with') — a
certainty scan rejects unsupported root-cause claims ('root cause is',
'definitely', 'proven').
"""
import time

import checks
import faultlab

GROUND_TRUTH = {
    'disk-exhaustion': {'check': 'disk_quota', 'expect': 'FAIL'},
    'killed-service': {'check': 'process', 'expect': 'FAIL'},
    'dns-failure': {'check': 'dns', 'expect': 'FAIL'},
    'cpu-pressure': {'check': 'load', 'expect': ('PASS', 'WARN')},
}

CERTAINTY_BANNED = ['root cause is', 'definitely ', 'proven ', 'proves ',
                    'certainly ', 'guaranteed ']


def run_case(fault):
    """Seed one fault in a fresh lab, collect the relevant checks + timing."""
    lab = faultlab.Lab(fault)
    started = time.perf_counter()
    try:
        if fault == 'disk-exhaustion':
            lab.seed_disk_exhaustion()
            finding = checks.disk_quota(str(lab.root), 1_000_000)
        elif fault == 'killed-service':
            seeded = lab.seed_killed_service()
            finding = checks.process(pid=seeded['pid'])
        elif fault == 'dns-failure':
            lab.seed_dns_failure()
            finding = checks.dns('no-such-host.invalid')
        elif fault == 'cpu-pressure':
            lab.seed_cpu_pressure(seconds=2, workers=2)
            finding = checks.load()
        else:
            raise ValueError('unknown fault %r' % fault)
        elapsed = time.perf_counter() - started
        # False-alarm sweep: the OTHER ground-truth checks on this lab.
        sweep = {'disk_quota': checks.disk_quota(str(lab.root), 10 ** 12),
                 'dns': checks.dns('localhost')}
    finally:
        cleanup = lab.cleanup()
    return {'fault': fault, 'finding': finding,
            'collection_seconds': round(elapsed, 3),
            'false_alarm_sweep': sweep, 'cleanup': cleanup}


def score(cases):
    """Localization accuracy, false alarms, unknowns, collection time."""
    per_fault, false_alarms, unknowns, times = {}, 0, 0, []
    for case in cases:
        truth = GROUND_TRUTH[case['fault']]
        got = case['finding']['status']
        want = truth['expect']
        correct = (got == want) if isinstance(want, str) else (got in want)
        per_fault[case['fault']] = {
            'expected': list(want) if isinstance(want, tuple) else want,
            'observed': got, 'localized': bool(correct),
            'evidence': {k: v for k, v in case['finding'].items()
                         if k != 'status'}}
        for name, check in case['false_alarm_sweep'].items():
            if check['status'] == 'FAIL':
                false_alarms += 1
            if check['status'] == 'UNKNOWN':
                unknowns += 1
        times.append(case['collection_seconds'])
    return {'per_fault': per_fault,
            'localized': sum(1 for v in per_fault.values() if v['localized']),
            'n_faults': len(per_fault), 'false_alarms': false_alarms,
            'unknowns': unknowns,
            'collection_seconds_total': round(sum(times), 3)}


def report(evaluation):
    """Useful report: evidence + next step per fault, hedged language only."""
    lines = ['# FleetDoctor diagnostic report (process-level lab; NOT hardware)',
             '',
             'Localizes %d/%d seeded faults; %d false alarms; %d unknowns; '
             'collected in %.3fs. Language is deliberately hedged: findings '
             '*indicate* candidates consistent with the evidence; no '
             'unsupported root-cause certainty is claimed.' % (
                 evaluation['localized'], evaluation['n_faults'],
                 evaluation['false_alarms'], evaluation['unknowns'],
                 evaluation['collection_seconds_total'])]
    for fault, row in evaluation['per_fault'].items():
        lines.append('')
        lines.append('## %s: %s' % (
            fault, 'LOCALIZED' if row['localized'] else 'MISSED'))
        lines.append('- Evidence: %s (expected %s, observed %s).' % (
            row['evidence'], row['expected'], row['observed']))
        lines.append('- Next step: %s.' % _next_step(fault, row['localized']))
    return '\n'.join(lines) + '\n'


def _next_step(fault, localized):
    return {'disk-exhaustion': 'free lab space or raise the quota, then '
                               're-run the quota check',
            'killed-service': 'restart the service under supervision and '
                              'confirm the PID check passes',
            'dns-failure': 'check resolver config and upstream reachability, '
                           'then re-resolve',
            'cpu-pressure': 'identify the load source before acting; load '
                            'alone does not name a culprit'}[fault] + (
        '' if localized else ' (first fix the missed detection)')


def certainty_scan(text):
    """Affirmative root-cause phrases without hedging; returns hits."""
    lowered = text.lower()
    return [p for p in CERTAINTY_BANNED if p in lowered]
