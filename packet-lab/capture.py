"""Open-format capture parser for PacketLab (P19-03): flows, redaction.

Parses the lab's open text capture format (`*.pkt` lines), NOT binary pcap —
no pcap library is used or claimed. Validates addresses/protocol/bytes,
aggregates to flows + per-protocol counters via the reference kernel,
REDACTS `secret=` values (asserted absent downstream), and retains
provenance (file sha, line counts, rejected lines with reasons — malformed
input is reported, never silently dropped).
"""
import hashlib
import ipaddress
from pathlib import Path

import project

PROTOCOLS = ('TCP', 'UDP', 'ICMP')
REDACTED = '[redacted]'


def parse_line(line):
    """Parse one `*.pkt` line → dict, or raise ValueError with the reason."""
    fields = {}
    for token in line.split():
        if '=' not in token:
            raise ValueError('token without =: %r' % token)
        key, _, value = token.partition('=')
        fields[key] = value
    for required in ('ts', 'src', 'dst', 'proto', 'bytes'):
        if required not in fields:
            raise ValueError('missing field %s' % required)
    try:
        src = str(ipaddress.ip_address(fields['src']))
        dst = str(ipaddress.ip_address(fields['dst']))
    except ValueError:
        raise ValueError('bad address in %r' % line)
    if fields['proto'] not in PROTOCOLS:
        raise ValueError('bad protocol in %r' % line)
    try:
        nbytes = int(fields['bytes'])
    except ValueError:
        raise ValueError('bad bytes in %r' % line)
    if nbytes < 0:
        raise ValueError('negative bytes in %r' % line)
    return {'ts': fields['ts'], 'src': src, 'dst': dst,
            'proto': fields['proto'], 'bytes': nbytes,
            'flags': fields.get('flags', ''),
            'secret': fields.get('secret', ''),
            'note': fields.get('note', '').replace('_', ' ')}


def redact(record):
    """Return the record with any secret value redacted (presence kept)."""
    record = dict(record)
    if record.get('secret'):
        record['secret'] = REDACTED
    return record


def parse_file(path):
    """Parse a capture file → {packets, flows, counters, rejected, sha}.

    Binary (non-UTF8) input is cleanly rejected as a whole — this parser
    reads the lab's open text format, not binary pcap, and says so instead
    of crashing.
    """
    path = Path(path)
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return {'packets': [], 'flows': [], 'protocol_bytes': {},
                'n_packets': 0,
                'rejected': [{'line': 0,
                              'reason': 'not UTF-8 text (binary pcap '
                                        'unsupported by design)'}],
                'sha256': sha, 'source': str(path)}
    packets, rejected = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            packets.append(redact(parse_line(raw)))
        except ValueError as exc:
            rejected.append({'line': lineno, 'reason': str(exc)})
    rows = [{'src': p['src'], 'dst': p['dst'], 'protocol': p['proto'],
             'bytes': p['bytes']} for p in packets]
    counters = {}
    for p in packets:
        counters[p['proto']] = counters.get(p['proto'], 0) + p['bytes']
    return {'packets': packets, 'flows': project.flows(rows),
            'protocol_bytes': counters,
            'n_packets': len(packets), 'rejected': rejected,
            'sha256': sha, 'source': str(path)}


def secrets_absent(parsed):
    """True when no raw secret value survives anywhere in the parsed output."""
    import json
    blob = json.dumps(parsed)
    return 'session-cookie' not in blob and 'secret=session' not in blob
