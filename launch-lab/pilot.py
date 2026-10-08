"""Narrow pilot with ordered/time-windowed instrumentation (P17-02).

The pilot workflow is a minimal readiness check on a fixture. Every run
emits timestamped, session-scoped events (`started` -> `checked` ->
`completed`); the windowed funnel counts an activation only when the ordered
predecessors precede it inside the time window. Test accounts are separated
from real users (currently zero real users — dry-run only, never presented
as people).
"""
import time

STAGES = ('started', 'checked', 'completed')


def readiness_check(fixture, session_id, at=None, test_account=True,
                    clock=time.time):
    """The narrow pilot workflow: check a fixture, emit ordered events."""
    at = clock() if at is None else at
    events = []
    for i, stage in enumerate(STAGES):
        events.append({'id': '%s-%s' % (session_id, stage),
                       'session': session_id, 'type': stage,
                       'at': at + i, 'test_account': test_account,
                       'fixture': fixture})
    ok = bool(fixture and fixture.get('files') and fixture.get('gate'))
    events[-1]['completed_ok'] = ok
    return {'ok': ok, 'events': events}


def windowed_funnel(events, window_s=3600):
    """Ordered, time-windowed funnel; test accounts excluded from real counts.

    A user counts at a stage only with that stage's event AND all ordered
    predecessors from the same session inside `window_s`. Out-of-order or
    late events are reported as excluded with reasons. Returns real-user and
    test-account funnels separately.
    """
    by_user = {}
    for event in events:
        if event['type'] not in STAGES:
            raise ValueError('unknown pilot event %r' % event['type'])
        by_user.setdefault((event.get('session'), event.get('user', event.get('session'))), []).append(event)
    real, test, excluded = {}, {}, []
    for (session, user), evs in by_user.items():
        ordered = sorted(evs, key=lambda e: e['at'])
        bucket = test if any(e.get('test_account') for e in ordered) else real
        seen_at = {}
        for event in ordered:
            idx = STAGES.index(event['type'])
            if idx > 0:
                prev = STAGES[idx - 1]
                if prev not in seen_at:
                    excluded.append({'event': event['id'],
                                     'reason': 'predecessor %s missing' % prev})
                    continue
                if event['at'] - seen_at[prev] > window_s:
                    excluded.append({'event': event['id'],
                                     'reason': 'outside %ss window' % window_s})
                    continue
            seen_at[event['type']] = event['at']
            bucket.setdefault(user, set()).add(event['type'])
    def funnel(bucket):
        started = {u for u, s in bucket.items() if 'started' in s}
        checked = {u for u in started if 'checked' in bucket[u]}
        done = {u for u in checked if 'completed' in bucket[u]}
        return {'started': len(started), 'checked': len(checked),
                'completed': len(done),
                'completion_per_start': (len(done) / len(started))
                if started else None}
    return {'real': funnel(real), 'test': funnel(test),
            'real_users': len(real), 'test_users': len(test),
            'excluded': excluded,
            'note': 'real users are consenting people; test accounts are '
                    'dry-runs and never counted as users'}
