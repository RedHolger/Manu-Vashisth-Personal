"""Versioned event ingestion for CohortLens (P08-01): schema checks plus a
SQLite store that enforces the same rules the Python kernel assumes.

Schema v1: events(id, user_id, type, at, ingested_at) — all UTC ISO-8601 with
an explicit offset. The store rejects unknown keys, naive timestamps and
conflicting duplicates (same id, different user/type/at); identical repeats
collapse to one row. Anything the store accepts, the metrics can read.
"""
import datetime as dt
import sqlite3

SCHEMA_VERSION = 1
REQUIRED_KEYS = frozenset({'id', 'user', 'type', 'at', 'ingested_at'})
UTC = dt.timezone.utc

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS events (
  id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  type TEXT NOT NULL,
  at TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  PRIMARY KEY (id, user_id, type, at)
);
CREATE TABLE IF NOT EXISTS user_segments (
  user_id TEXT PRIMARY KEY,
  segment TEXT NOT NULL
);
"""


def parse_utc(value):
    """Strict UTC instant; naive or unparsable input is rejected."""
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string, got %r' % (value,))
    try:
        moment = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('unparseable timestamp %r' % (value,))
    if moment.tzinfo is None:
        raise ValueError('timezone required in %r' % (value,))
    return moment.astimezone(UTC)


def validate_event(event):
    """Schema v1 check; returns a normalized row or raises ValueError."""
    if set(event) != REQUIRED_KEYS:
        raise ValueError('event keys must be exactly %s'
                         % sorted(REQUIRED_KEYS))
    if not event['id'] or not event['user']:
        raise ValueError('id and user must be non-empty')
    user = event['user']
    at = parse_utc(event['at'])
    ingested = parse_utc(event['ingested_at'])
    return {'id': str(event['id']), 'user_id': str(user),
            'type': str(event['type']),
            'at': at.isoformat(), 'ingested_at': ingested.isoformat()}


def connect(path=':memory:'):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    row = conn.execute(
        'SELECT version FROM schema_version').fetchone()
    if row is None:
        conn.execute('INSERT INTO schema_version (version) VALUES (?)',
                     (SCHEMA_VERSION,))
    elif row[0] != SCHEMA_VERSION:
        raise ValueError('schema v%s data, this code reads v%s'
                         % (row[0], SCHEMA_VERSION))
    conn.commit()
    return conn


def ingest(conn, events):
    """Validate and store; returns {stored, duplicates, conflicts}.

    Identical repeats are idempotent (one row survives). A conflicting
    duplicate aborts the batch with ValueError — the store never has to guess
    which version of an event is true.
    """
    stored, duplicates = 0, 0
    for event in events:
        row = validate_event(event)
        clash = conn.execute(
            'SELECT user_id, type, at FROM events WHERE id = ?',
            (row['id'],)).fetchall()
        if any((user, kind, at) != (row['user_id'], row['type'], row['at'])
               for user, kind, at in clash):
            raise ValueError('conflicting duplicate event %r' % row['id'])
        cursor = conn.execute(
            'INSERT OR IGNORE INTO events (id, user_id, type, at, '
            'ingested_at) VALUES (?, ?, ?, ?, ?)',
            (row['id'], row['user_id'], row['type'], row['at'],
             row['ingested_at']))
        stored += cursor.rowcount
        duplicates += 1 - cursor.rowcount
    conn.commit()
    return {'stored': stored, 'duplicates': duplicates, 'conflicts': 0}


def set_segments(conn, mapping):
    """Store user_id -> segment labels; unknown users stay unmapped.

    Labels must be non-empty strings; user ids non-empty. Returns the
    number of rows written. Unmapped users read back as 'unknown' in
    segments.py / segments.sql — they are never silently dropped or
    counted as zero.
    """
    if not isinstance(mapping, dict):
        raise ValueError('segments must be a dict, got %r' % (mapping,))
    count = 0
    for user_id, segment in mapping.items():
        if not isinstance(user_id, str) or not user_id:
            raise ValueError('user_id must be a non-empty string')
        if not isinstance(segment, str) or not segment:
            raise ValueError('segment must be a non-empty string')
        conn.execute(
            'INSERT OR REPLACE INTO user_segments (user_id, segment) '
            'VALUES (?, ?)', (user_id, segment))
        count += 1
    conn.commit()
    return count


def get_segments(conn):
    """Return the stored user_id -> segment mapping."""
    return dict(conn.execute('SELECT user_id, segment FROM user_segments'
                            ).fetchall())
