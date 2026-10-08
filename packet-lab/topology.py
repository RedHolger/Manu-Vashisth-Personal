"""Versioned lab topology + admin guard for PacketLab (P19-01).

The topology is a versioned SPECIFICATION (hosts, router, service, subnets
from documentation ranges). No live namespace/VM exists here (macOS has no
netns; no hypervisor/admin was granted), so there is no live topology to
observe — the healthy baseline is a MODEL self-check, labeled as such, and
every admin operation is a dry-run plan that REFUSES non-lab targets and
refuses to execute privileged commands. The guard is real and tested; the
live topology is BLOCKED.
"""
TOPOLOGY = {'version': 'v1', 'hosts': ['lab-h1', 'lab-h2'],
            'router': 'lab-r1', 'service': 'lab-svc',
            'subnets': {'lan': '198.51.100.0/24', 'wan': '203.0.113.0/24'},
            'allowlist': ['lab-h1', 'lab-h2', 'lab-r1', 'lab-svc'],
            'live': False}


class Refused(RuntimeError):
    pass


class BlockedError(RuntimeError):
    pass


def admin_op(target, action):
    """Plan an admin operation. Refuses non-lab targets and live execution.

    Returns a dry-run record. Never executes anything privileged and never
    touches a target outside the allowlist (no scanning of unrelated
    networks — there is no scanning at all).
    """
    if target not in TOPOLOGY['allowlist']:
        raise Refused('target %r is not a named lab resource; refusing '
                      '(no operation on outside networks)' % (target,))
    if action not in ('up', 'down', 'reset', 'capture'):
        raise Refused('unknown admin action %r' % (action,))
    return {'target': target, 'action': action, 'executed': False,
            'mode': 'dry-run (no live topology; netns/VM BLOCKED)'}


def healthy_baseline():
    """Model self-check of the specified topology (MODEL, not live)."""
    checks = [{'resource': r, 'modeled_state': 'up'}
              for r in TOPOLOGY['allowlist']]
    checks.append({'resource': 'lab-svc', 'modeled_state': 'answering',
                   'note': 'model answer; no live service probed'})
    return {'topology_version': TOPOLOGY['version'], 'kind': 'MODEL BASELINE '
            '(no live namespaces/VMs here)', 'checks': checks,
            'healthy': all(c['modeled_state'] in ('up', 'answering')
                           for c in checks)}


def live_topology():
    raise BlockedError('no live topology: network namespaces unavailable on '
                       'this host and no VM/admin grant exists; use the '
                       'fixture scenarios (P19-02) instead')
