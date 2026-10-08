"""Licensed/authorized event-stream adapter for CohortLens (P08-04).

load_csv_events() reads an external CSV with columns
id,user,type,at,ingested_at (+ optional segment) and returns v1 events
plus a segment mapping, reusing the same UTC validation as ingest.py.
No product stream is bundled: the caller supplies the file, its source
URL, license and retrieval time, and write_manifest() freezes those facts
plus sha256, row counts and time range into a JSON manifest. Synthetic
fixtures remain the only measured evidence until a real stream arrives.
"""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from ingest import parse_utc

COLUMNS = ('id', 'user', 'type', 'at', 'ingested_at')
ALLOWED_TYPES = frozenset({'signup', 'activate', 'active'})


def load_csv_events(path):
    """Load and validate an external CSV; returns (events, segments)."""
    path = Path(path)
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError('CSV has no header row')
        extras = [name for name in reader.fieldnames
                  if name not in COLUMNS + ('segment',)]
        if extras:
            raise ValueError('unexpected CSV columns %r' % (extras,))
        missing = [name for name in COLUMNS if name not in reader.fieldnames]
        if missing:
            raise ValueError('missing CSV columns %r' % (missing,))
        events, segments = [], {}
        for lineno, row in enumerate(reader, start=2):
            if not row['id'] or not row['user']:
                raise ValueError('line %d: id and user must be non-empty'
                                 % lineno)
            if row['type'] not in ALLOWED_TYPES:
                raise ValueError("line %d: type must be one of %s"
                                 % (lineno, sorted(ALLOWED_TYPES)))
            parse_utc(row['at'])
            parse_utc(row['ingested_at'])
            events.append({'id': row['id'], 'user': row['user'],
                           'type': row['type'], 'at': row['at'],
                           'ingested_at': row['ingested_at']})
            if 'segment' in reader.fieldnames and row.get('segment'):
                segments[row['user']] = row['segment']
    if not events:
        raise ValueError('CSV contains no event rows')
    ids = [event['id'] for event in events]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate event ids in CSV')
    return events, segments


def write_manifest(csv_path, source_url, license_name, retrieved_at,
                   out_path):
    """Freeze provenance for an external CSV; returns the manifest dict."""
    csv_path = Path(csv_path)
    raw = csv_path.read_bytes()
    events, segments = load_csv_events(csv_path)
    stamps = [parse_utc(event['at']) for event in events]
    manifest = {
        'source': str(csv_path.name),
        'source_url': source_url,
        'license': license_name,
        'retrieved_at': parse_utc(retrieved_at).isoformat(),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw),
        'rows': len(events),
        'users': len({event['user'] for event in events}),
        'segments': len(set(segments.values())) if segments else 0,
        'min_at': min(stamps).isoformat(),
        'max_at': max(stamps).isoformat(),
        'adapter': 'real_data.load_csv_events (P08-04)',
    }
    out = Path(out_path)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')
    return manifest


def coverage_note(manifest):
    """One-paragraph coverage/privacy/retention note for a manifest."""
    return ('Coverage: %(rows)d events / %(users)d users from %(min_at)s to '
            '%(max_at)s (%(source)s, %(license)s). Privacy: user ids are '
            'treated as pseudonymous labels; no names, emails or free text '
            'are ingested. Retention: the CSV is read, not stored; the '
            'SQLite store is disposable per run.' % manifest)
