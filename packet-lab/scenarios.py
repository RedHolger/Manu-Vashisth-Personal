"""Break/fix scenario fixtures with ground truth + reset (P19-02).

Four fault cases as deterministic open-format capture records, each with
observable ground truth (fault, layer, expected symptom) and a byte-identical
regeneration reset. Fixtures use documentation-range IPs only. Live replay
needs the BLOCKED topology; the fixtures + reset proof are the deliverable.
"""
import hashlib
import json
from pathlib import Path

H1, H2, SVC = '198.51.100.11', '198.51.100.12', '203.0.113.80'

CASES = ('dns-fail', 'route-blackhole', 'mtu-clamp', 'conn-timeout')

GROUND_TRUTH = {
    'dns-fail': {'fault': 'lab resolver returns NXDOMAIN for lab-svc',
                 'layer': 'dns', 'symptom': 'no address; nothing leaves h1'},
    'route-blackhole': {'fault': 'lab-r1 drops h1->svc',
                        'layer': 'route',
                        'symptom': 'address resolves; no replies; TTLs die'},
    'mtu-clamp': {'fault': 'path MTU 1280, 1500B sends need fragmentation',
                  'layer': 'tcp',
                  'symptom': 'small packets pass; 1500B stall (DF set)'},
    'conn-timeout': {'fault': 'service accepts then stalls 30s',
                     'layer': 'application',
                     'symptom': 'TCP up; no banner; client times out'},
}


def _pkt(ts, src, dst, proto, nbytes, flags='', secret='', note=''):
    parts = ['ts=%s' % ts, 'src=%s' % src, 'dst=%s' % dst, 'proto=%s' % proto,
             'bytes=%d' % nbytes]
    if flags:
        parts.append('flags=%s' % flags)
    if secret:
        parts.append('secret=%s' % secret)
    if note:
        parts.append('note=%s' % note.replace(' ', '_'))
    return ' '.join(parts)


def fixture(case):
    t0 = '2026-02-01T10:00:00+00:00'
    if case == 'dns-fail':
        return [_pkt(t0, H1, H1, 'UDP', 64, note='dns query lab-svc'),
                _pkt(t0, H1, H1, 'UDP', 96, note='dns NXDOMAIN lab-svc')]
    if case == 'route-blackhole':
        return [_pkt(t0, H1, SVC, 'TCP', 60, flags='SYN'),
                _pkt(t0, H1, SVC, 'TCP', 60, flags='SYN'),
                _pkt(t0, H1, SVC, 'ICMP', 72, note='ttl-exceeded r1')]
    if case == 'mtu-clamp':
        return [_pkt(t0, H1, SVC, 'TCP', 64, flags='SYN+ACK-small-ok'),
                _pkt(t0, H1, SVC, 'TCP', 1500, flags='DF',
                     secret='session-cookie-abc123'),
                _pkt(t0, H1, SVC, 'ICMP', 128,
                     note='frag-needed mtu-1280')]
    if case == 'conn-timeout':
        return [_pkt(t0, H1, SVC, 'TCP', 60, flags='SYN'),
                _pkt(t0, SVC, H1, 'TCP', 60, flags='SYN+ACK'),
                _pkt(t0, H1, SVC, 'TCP', 52, flags='ACK'),
                _pkt(t0, H1, SVC, 'TCP', 52, flags='PSH-no-reply')]
    raise ValueError('unknown case %r' % (case,))


def write_fixtures(root):
    """Deterministic fixture set + manifest (sha per file + corpus)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in CASES:
        path = root / ('%s.pkt' % case)
        path.write_text('\n'.join(fixture(case)) + '\n', encoding='utf-8')
        data = path.read_bytes()
        rows.append({'case': case, 'path': path.name,
                     'sha256': hashlib.sha256(data).hexdigest(),
                     'lines': len(fixture(case))})
        (root / ('%s.groundtruth.json' % case)).write_text(
            json.dumps(GROUND_TRUTH[case], indent=2, sort_keys=True) + '\n')
    manifest = {'generator': 'scenarios.write_fixtures()', 'synthetic': True,
                'files': rows,
                'corpus_sha256': hashlib.sha256(
                    '\n'.join(r['sha256'] for r in rows).encode()
                ).hexdigest()}
    (root / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def reset_check(root):
    """Regenerate and prove byte-identical reset (same corpus sha)."""
    import tempfile
    before = json.loads((Path(root) / 'manifest.json').read_text())
    with tempfile.TemporaryDirectory() as tmp:
        after = write_fixtures(tmp)
    return {'reset_reproducible': after['corpus_sha256'] ==
            before['corpus_sha256'],
            'corpus_sha256': before['corpus_sha256']}
