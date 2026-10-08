"""Launch experiment + decision memo for LaunchLab (P17-03/04).

Message comprehension is scored on LABELED test sessions only — never as
marketing conversion or revenue. Publishing/external messages need explicit
user authorization (`publish()` raises without it). The decision memo keeps
conflicting feedback and refuses fabricated uplift, quotes or revenue: those
claims need real-user evidence that does not exist here.
"""
MESSAGES = {
    'A': 'Know before you ship: a readiness check for your review bundle.',
    'B': 'Stop guessing release readiness. Check the artifacts, not vibes.',
}


class AuthorizationRequired(RuntimeError):
    pass


class FabricationError(RuntimeError):
    pass


def comprehension(sessions):
    """Score message comprehension on labeled test sessions.

    Each session: {variant: A/B, understood: bool, test_account: bool}.
    Real-user sessions are rejected here (none exist); only test sessions
    score, and the output is labeled comprehension, never conversion.
    """
    for session in sessions:
        if not session.get('test_account'):
            raise FabricationError('real-user session in a test-only '
                                   'comprehension run refused')
        if session.get('variant') not in MESSAGES:
            raise ValueError('unknown variant')
    by_variant = {}
    for session in sessions:
        bucket = by_variant.setdefault(session['variant'],
                                       {'n': 0, 'understood': 0})
        bucket['n'] += 1
        bucket['understood'] += int(bool(session.get('understood')))
    return {'metric': 'comprehension (test sessions only; NOT conversion)',
            'by_variant': by_variant,
            'sessions': len(sessions), 'real_users': 0}


def publish(kind, authorized=False, authorizer=None, scope=None):
    """Publish a demo/landing page or send external messages.

    Requires explicit user authorization naming who approved and what scope.
    Without it this raises — publishing is BLOCKED, not simulated.
    """
    if not (authorized and authorizer and scope):
        raise AuthorizationRequired(
            'public publishing needs applicable user authorization '
            '(authorizer + scope); refusing to publish %r' % kind)
    return {'published': kind, 'authorizer': authorizer, 'scope': scope}


def decide(observations, real_users=0):
    """Keep/change/stop memo from observed outcomes + conflicting feedback.

    `observations`: list of {finding, supports (keep/change/stop), conflicts}.
    Conflicts are retained, not resolved silently. A real decision needs real
    users; with none, the memo recommends STOP-or-wait and says so.
    """
    if real_users == 0:
        verdict, reason = 'STOP (wait for real users)', \
            'no real-user evidence; test outcomes cannot authorize a launch'
    else:
        votes = {}
        for obs in observations:
            votes[obs['supports']] = votes.get(obs['supports'], 0) + 1
        verdict = max(votes, key=votes.get)
        reason = 'majority of %d observations' % len(observations)
    conflicts = [o for o in observations if o.get('conflicts')]
    return {'verdict': verdict, 'reason': reason,
            'observations': len(observations),
            'conflicting_feedback_retained': len(conflicts),
            'real_users': real_users}


def claim_validator(kind, real_user_evidence=0):
    """Refuse uplift/quote/revenue claims without real-user evidence."""
    if kind in ('conversion-uplift', 'customer-quote', 'business-revenue'):
        if real_user_evidence <= 0:
            raise FabricationError(
                'a %s claim without real-user evidence is refused' % kind)
    return {'claim': kind, 'basis': 'real-user evidence n=%d'
            % real_user_evidence}
