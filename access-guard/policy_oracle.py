"""Trusted expected-policy oracle for AccessGuard (P11).

Independent of the lab target app: this module never imports `lab_app`. It
parses the same token contract from the policy side and decides allow/deny
with a reason. Any disagreement between the oracle and the app is a finding
against the app — the oracle is never altered to match app bugs.

Policy (server-side enforcement):
- Unknown/malformed token, unknown user, revoked user or expired session
  -> deny (fail closed).
- Unknown action or unknown resource -> deny (fail closed).
- Cross-tenant access -> deny, even for admins and even on owner-id match.
- Role comes from the server-side registry, never from the token's claimed
  role (forged elevation is denied).
- read/write: admin (own tenant) or the resource owner. delete: admin only.
"""
import time

ACTIONS = {'GET': 'read', 'POST': 'write', 'DELETE': 'delete'}

REGISTRY = {'alice': 'admin', 'bob': 'member', 'carol': 'member',
            'dave': 'member', 'erin': 'member'}
USER_TENANT = {'alice': 'A', 'bob': 'A', 'carol': 'B', 'dave': 'A',
               'erin': 'A'}
REVOKED = frozenset({'erin'})
DOCS = {('A', 'doc1'): 'alice', ('A', 'doc2'): 'bob',
        ('B', 'doc1'): 'carol', ('B', 'doc2'): 'bob'}

FUTURE = 4102444800
PAST = 1000000000


def make_token(user, role=None, exp=FUTURE):
    return 'tok-%s-%s-%s-%d' % (user, USER_TENANT[user],
                                role or REGISTRY[user], exp)


TOKENS = {
    'alice_admin': make_token('alice'),
    'bob_member': make_token('bob'),
    'carol_member': make_token('carol'),
    'dave_expired': make_token('dave', exp=PAST),
    'erin_revoked': make_token('erin'),
    'alice_expired_admin': make_token('alice', exp=PAST),
    'forged_bob_admin': make_token('bob', role='admin'),
    'forged_alice_admin_after_demotion': make_token('alice', role='admin'),
}
MALFORMED_TOKENS = ['not-a-token', 'tok-bob', 'tok---', '', 'tok-bob-A-member']


def parse(token):
    """Split a token into (user, tenant, claimed_role, exp); None if malformed."""
    if not isinstance(token, str):
        return None
    parts = token.split('-')
    if len(parts) != 5 or parts[0] != 'tok':
        return None
    _, user, tenant, claimed_role, exp = parts
    if user not in REGISTRY or tenant not in ('A', 'B') \
            or claimed_role not in ('admin', 'member'):
        return None
    try:
        exp = int(exp)
    except ValueError:
        return None
    return user, tenant, claimed_role, exp


def expected(token, method, tenant, doc, registry=None, revoked=None, now=None):
    """Return ``(allow: bool, reason: str)`` for one request."""
    registry = REGISTRY if registry is None else registry
    revoked = REVOKED if revoked is None else revoked
    now = time.time() if now is None else now
    if method not in ACTIONS:
        return False, 'unknown-action'
    parsed = parse(token)
    if parsed is None:
        return False, 'malformed-or-unknown-token'
    user, _, _, exp = parsed
    if user in revoked:
        return False, 'revoked'
    if exp < now:
        return False, 'expired'
    owner = DOCS.get((tenant, doc))
    if owner is None:
        return False, 'unknown-resource'
    if USER_TENANT[user] != tenant:
        return False, 'cross-tenant'
    role = registry.get(user, 'member')
    action = ACTIONS[method]
    if role == 'admin':
        return True, 'admin-own-tenant'
    if user == owner and action in ('read', 'write'):
        return True, 'owner-read-write'
    if action == 'delete':
        return False, 'delete-requires-admin'
    return False, 'not-owner-or-admin'
