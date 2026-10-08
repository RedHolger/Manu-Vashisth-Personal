"""HTTP case runner for AccessGuard (P11): oracle-expected vs app-actual.

Every case is a REAL HTTP request (stdlib urllib) against a FRESH lab-app
server on 127.0.0.1, so one case can never pollute another (DELETE included).
The trusted oracle (`policy_oracle.expected`) supplies the expected outcome;
records are SANITIZED — they carry the principal id, never the bearer token.
"""
import urllib.request
import urllib.error

import lab_app
import policy_oracle as oracle

DEMOTED_REGISTRY = dict(oracle.REGISTRY, alice='member')
REVOKED_ALICE = frozenset({'alice'})


def _request(base, token, method, tenant, doc):
    url = '%s/docs/%s/%s' % (base, tenant, doc)
    req = urllib.request.Request(url, method=method)
    if token is not None:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, True
    except urllib.error.HTTPError as exc:
        return exc.code, False
    except Exception as exc:  # connection failure is a finding, not a pass
        return 'error:%s' % type(exc).__name__, False


def _principal(token):
    parsed = oracle.parse(token)
    return parsed[0] if parsed else 'anonymous'


def generate_cases(which='focus'):
    """Return a list of case dicts. `focus` = P11-01 core; `extended` adds
    expiry, revocation, unknown action, malformed ids and privilege change."""
    T = oracle.TOKENS
    cases = [
        # happy-path allows (both variants must grant)
        dict(label='admin-read-own', token=T['alice_admin'], method='GET',
             tenant='A', doc='doc1'),
        dict(label='owner-read-own', token=T['bob_member'], method='GET',
             tenant='A', doc='doc2'),
        dict(label='owner-write-own', token=T['bob_member'], method='POST',
             tenant='A', doc='doc2'),
        dict(label='admin-delete-own', token=T['alice_admin'],
             method='DELETE', tenant='A', doc='doc2'),
        dict(label='member-read-own-tenant', token=T['carol_member'],
             method='GET', tenant='B', doc='doc1'),
        # baseline denies (both variants must deny)
        dict(label='member-read-others', token=T['bob_member'], method='GET',
             tenant='A', doc='doc1'),
        dict(label='member-delete-needs-admin', token=T['bob_member'],
             method='DELETE', tenant='A', doc='doc2'),
        dict(label='member-cross-tenant', token=T['carol_member'],
             method='GET', tenant='A', doc='doc1'),
        # PLANTED cross-tenant attacks (oracle denies; vulnerable grants)
        dict(label='attack-admin-cross-tenant-read',
             token=T['alice_admin'], method='GET', tenant='B', doc='doc1'),
        dict(label='attack-owner-id-confusion',
             token=T['bob_member'], method='GET', tenant='B', doc='doc2'),
        dict(label='attack-admin-cross-tenant-write',
             token=T['alice_admin'], method='POST', tenant='B', doc='doc1'),
        # PLANTED object-ownership attacks (oracle denies; vulnerable grants)
        dict(label='attack-member-write-others',
             token=T['bob_member'], method='POST', tenant='A', doc='doc1'),
        dict(label='attack-member-write-foreign-tenant',
             token=T['carol_member'], method='POST', tenant='B', doc='doc2'),
    ]
    if which == 'extended':
        cases += [
            dict(label='expired-session', token=T['dave_expired'],
                 method='GET', tenant='A', doc='doc1'),
            dict(label='revoked-session', token=T['erin_revoked'],
                 method='GET', tenant='A', doc='doc1'),
            dict(label='expired-admin-bypass', token=T['alice_expired_admin'],
                 method='GET', tenant='A', doc='doc1'),
            dict(label='revoked-admin-bypass', token=T['alice_admin'],
                 method='GET', tenant='A', doc='doc1',
                 revoked='alice'),
            dict(label='unknown-action', token=T['alice_admin'],
                 method='PUT', tenant='A', doc='doc1'),
            dict(label='malformed-token', token=oracle.MALFORMED_TOKENS[0],
                 method='GET', tenant='A', doc='doc1'),
            dict(label='unknown-resource', token=T['alice_admin'],
                 method='GET', tenant='A', doc='no-such-doc'),
            dict(label='privilege-demotion-denies',
                 token=T['forged_alice_admin_after_demotion'],
                 method='DELETE', tenant='A', doc='doc1',
                 registry='demoted'),
            dict(label='forged-admin-claim-denied',
                 token=T['forged_bob_admin'], method='GET', tenant='A',
                 doc='doc1'),
        ]
    return cases


def _imports_module(source, module):
    """True only if `source` has a real import of `module` (not a mention)."""
    for line in source.splitlines():
        stripped = line.strip()
        if (stripped.startswith('import ') or stripped.startswith('from ')) \
                and module in stripped.split():
            return True
    return False


def evaluate(bugs, which='focus'):
    """Run every case over real HTTP; return the sanitized report.

    One shared server per registry (default + demoted) serves all
    non-mutating cases; each DELETE runs on a FRESH server so a successful
    delete can never pollute another case. Every server is loopback-only.
    """
    bugs = frozenset(bugs)
    violations = []
    records = []
    shared = {}
    try:
        for case in generate_cases(which):
            key = case.get('registry') or 'default'
            registry = (DEMOTED_REGISTRY if key == 'demoted' else None)
            revoked = (REVOKED_ALICE if case.get('revoked') == 'alice'
                       else None)
            if case['method'] == 'DELETE':
                server, _, base = lab_app.serve(bugs, registry=registry,
                                                revoked=revoked)
                fresh = True
            else:
                skey = (key, case.get('revoked') or '-')
                if skey not in shared:
                    server, _, base = lab_app.serve(bugs, registry=registry,
                                                    revoked=revoked)
                    shared[skey] = server
                else:
                    server = shared[skey]
                    base = 'http://127.0.0.1:%d' % server.server_address[1]
                fresh = False
            try:
                status, actual_allow = _request(base, case['token'],
                                                case['method'], case['tenant'],
                                                case['doc'])
            finally:
                if fresh:
                    lab_app.stop(server)
            allow, reason = oracle.expected(case['token'], case['method'],
                                            case['tenant'], case['doc'],
                                            registry=registry,
                                            revoked=revoked)
            record = {'label': case['label'],
                      'principal': _principal(case['token']),
                      'method': case['method'],
                      'resource_tenant': case['tenant'], 'doc': case['doc'],
                      'expected': allow, 'expected_reason': reason,
                      'actual_status': status, 'actual_allow': actual_allow}
            records.append(record)
            if allow != actual_allow:
                violations.append(record)
    finally:
        for server in shared.values():
            lab_app.stop(server)
    return {'cases': len(records), 'mismatches': len(violations),
            'violations': violations, 'records': records,
            'bugs': sorted(bugs), 'which': which,
            'oracle_module': 'policy_oracle (independent; never altered)'}


def summarize(report):
    lines = ['cases=%d mismatches=%d [%s]' % (
        report['cases'], report['mismatches'], report['which'])]
    for v in report['violations']:
        lines.append('  MISMATCH %s: %s %s/%s expected=%s(%s) actual=%s' % (
            v['label'], v['principal'], v['resource_tenant'], v['doc'],
            v['expected'], v['expected_reason'], v['actual_status']))
    return '\n'.join(lines)
