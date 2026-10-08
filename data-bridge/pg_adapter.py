"""PostgreSQL page adapter: data, quarantine and checkpoint in one transaction.

Ports the reference SQLite `Importer` contract to PostgreSQL and adds the fields
P06-02 requires: source snapshot identity and checksum on `runs`, original record
identity (`origin_id`), the normalized identifier (`normalized_id`) and the
normalize-or-quarantine decision (`decision`) on every row of `raw`.

One call to :meth:`PgImporter.step` is exactly one SQL transaction, so a crash
anywhere inside a page — after the raw rows, after the quarantine decisions, or
before the checkpoint update — leaves none of it behind.
"""
import csv
import hashlib
import io
import json
import os

import psycopg
import psycopg.rows

from project import IntegrityError, digest, normalize

DEFAULT_DSN = os.environ.get(
    'P06_DATABASE_URL',
    'postgresql://databridge:databridge@127.0.0.1:5434/databridge')

DECISIONS = ('normalized', 'quarantined')

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    source   TEXT PRIMARY KEY,
    snapshot TEXT NOT NULL,
    cursor   TEXT,
    done     INTEGER NOT NULL DEFAULT 0,
    seen     INTEGER NOT NULL DEFAULT 0,
    checksum TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw (
    source        TEXT NOT NULL,
    position      INTEGER NOT NULL,
    origin_id     TEXT,
    normalized_id TEXT,
    decision      TEXT NOT NULL CHECK (decision IN ('normalized', 'quarantined')),
    payload       TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    PRIMARY KEY (source, position)
);
CREATE TABLE IF NOT EXISTS orders (
    source   TEXT NOT NULL,
    id       TEXT NOT NULL,
    customer TEXT NOT NULL,
    cents    INTEGER NOT NULL,
    PRIMARY KEY (source, id)
);
CREATE TABLE IF NOT EXISTS quarantine (
    source   TEXT NOT NULL,
    position INTEGER NOT NULL,
    reason   TEXT NOT NULL,
    origin_id TEXT,
    payload  TEXT NOT NULL,
    PRIMARY KEY (source, position)
);
"""

COMPLETENESS_SQL = """
SELECT r.position,
       r.origin_id,
       r.normalized_id,
       r.decision,
       r.payload_sha256,
       q.reason,
       (o.id IS NOT NULL) AS order_present
FROM raw r
LEFT JOIN quarantine q ON q.source = r.source AND q.position = r.position
LEFT JOIN orders o ON o.source = r.source AND o.id = r.normalized_id
WHERE r.source = %(source)s
ORDER BY r.position
"""


def origin_id_of(row, schema):
    """The identifier the source itself gave the record, before normalization."""
    if not isinstance(row, dict):
        return None
    if schema == 'a':
        value = row.get('id')
    elif schema == 'b':
        value = row.get('order_id')
    else:
        value = None
    return value if isinstance(value, str) and value else None


class PgImporter:
    def __init__(self, dsn=DEFAULT_DSN):
        self.dsn = dsn
        self.conn = psycopg.connect(dsn, autocommit=False,
                                    row_factory=psycopg.rows.dict_row)
        with self.conn.transaction():
            self.conn.execute(SCHEMA)

    def step(self, name, source, schema, fail_before_commit=False):
        """Fetch one page and commit its rows, quarantine and checkpoint together."""
        with self.conn.transaction():
            record = self.conn.execute(
                'SELECT snapshot, cursor, done, seen, checksum FROM runs WHERE source = %s',
                (name,)).fetchone()
            if record and record['done']:
                return False
            cursor = record['cursor'] if record else '0'
            page = source.fetch(cursor)
            expected = record['seen'] if record else 0
            stored_snapshot = record['snapshot'] if record else None
            stored_checksum = record['checksum'] if record else None

            if page['start'] != expected or (
                    record and (page['snapshot'] != stored_snapshot
                                or page['checksum'] != stored_checksum)):
                raise IntegrityError('snapshot changed or missing page')

            end = expected + len(page['rows'])
            if page['next'] is not None and (not page['rows']
                                             or int(page['next']) != end):
                raise IntegrityError('non-advancing or skipped cursor')
            if page['next'] is None and end != page['total']:
                raise IntegrityError('truncated source')

            for offset, row in enumerate(page['rows']):
                position = expected + offset
                payload = json.dumps(row, sort_keys=True)
                payload_sha = hashlib.sha256(payload.encode('utf-8')).hexdigest()
                origin = origin_id_of(row, schema)
                try:
                    normalized = normalize(row, schema)
                except (ValueError, TypeError, KeyError) as exc:
                    self._record_row(name, position, origin, None, 'quarantined',
                                     payload, payload_sha)
                    self.conn.execute(
                        'INSERT INTO quarantine (source, position, reason, origin_id, payload)'
                        ' VALUES (%s, %s, %s, %s, %s)',
                        (name, position, str(exc), origin, payload))
                    continue

                existing = self.conn.execute(
                    'SELECT customer, cents FROM orders WHERE source = %s AND id = %s',
                    (name, normalized['id'])).fetchone()
                if existing and (existing['customer'], existing['cents']) != (
                        normalized['customer'], normalized['cents']):
                    reason = 'conflicting duplicate ID in immutable snapshot'
                    self._record_row(name, position, origin, normalized['id'],
                                     'quarantined', payload, payload_sha)
                    self.conn.execute(
                        'INSERT INTO quarantine (source, position, reason, origin_id, payload)'
                        ' VALUES (%s, %s, %s, %s, %s)',
                        (name, position, reason, origin, payload))
                    continue

                self._record_row(name, position, origin, normalized['id'],
                                 'normalized', payload, payload_sha)
                self.conn.execute(
                    'INSERT INTO orders (source, id, customer, cents) VALUES (%s, %s, %s, %s)'
                    ' ON CONFLICT (source, id) DO NOTHING',
                    (name, normalized['id'], normalized['customer'], normalized['cents']))

            self.conn.execute(
                'INSERT INTO runs (source, snapshot, cursor, done, seen, checksum)'
                ' VALUES (%s, %s, %s, %s, %s, %s)'
                ' ON CONFLICT (source) DO UPDATE SET snapshot = excluded.snapshot,'
                ' cursor = excluded.cursor, done = excluded.done,'
                ' seen = excluded.seen, checksum = excluded.checksum',
                (name, page['snapshot'], page['next'], int(page['next'] is None),
                 end, page['checksum']))

            if page['next'] is None:
                payloads = [row['payload'] for row in self.conn.execute(
                    'SELECT payload FROM raw WHERE source = %s ORDER BY position',
                    (name,)).fetchall()]
                if digest([json.loads(text) for text in payloads]) != page['checksum']:
                    raise IntegrityError('content manifest mismatch')

            if fail_before_commit:
                raise RuntimeError('injected crash before commit')

        return page['next'] is not None

    def _record_row(self, name, position, origin, normalized_id, decision,
                    payload, payload_sha):
        self.conn.execute(
            'INSERT INTO raw (source, position, origin_id, normalized_id, decision,'
            ' payload, payload_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (name, position, origin, normalized_id, decision, payload, payload_sha))

    def report(self, name):
        record = self.conn.execute(
            'SELECT source, snapshot, cursor, done, seen, checksum FROM runs WHERE source = %s',
            (name,)).fetchone()
        orders = self.conn.execute(
            'SELECT COUNT(*) AS n FROM orders WHERE source = %s', (name,)).fetchone()['n']
        quarantine = [{'position': row['position'], 'reason': row['reason']}
                      for row in self.conn.execute(
                          'SELECT position, reason FROM quarantine WHERE source = %s'
                          ' ORDER BY position', (name,)).fetchall()]
        return {
            'source': name,
            'checkpoint': dict(record) if record else None,
            'valid_unique_orders': orders,
            'quarantine': quarantine,
        }

    def completeness(self, name):
        """Row-level completeness: one entry per source record position."""
        return [dict(row) for row in self.conn.execute(
            COMPLETENESS_SQL, {'source': name}).fetchall()]

    def export_completeness(self, name, path):
        rows = self.completeness(name)
        fieldnames = ['source', 'position', 'origin_id', 'normalized_id', 'decision',
                      'reason', 'payload_sha256', 'order_present']
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'source': name,
                'position': row['position'],
                'origin_id': row['origin_id'] or '',
                'normalized_id': row['normalized_id'] or '',
                'decision': row['decision'],
                'reason': row['reason'] or '',
                'payload_sha256': row['payload_sha256'],
                'order_present': 'true' if row['order_present'] else 'false',
            })
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(buffer.getvalue())

        normalized = sum(1 for row in rows if row['decision'] == 'normalized')
        distinct_orders = self.conn.execute(
            'SELECT COUNT(*) AS n FROM orders WHERE source = %s',
            (name,)).fetchone()['n']
        summary = {
            'source': name,
            'positions': len(rows),
            'normalized': normalized,
            'quarantined': len(rows) - normalized,
            'distinct_orders': distinct_orders,
            'rows_with_order': sum(1 for row in rows if row['order_present']),
            'normalized_without_order': sum(
                1 for row in rows
                if row['decision'] == 'normalized' and not row['order_present']),
            'quarantined_with_order': sum(
                1 for row in rows
                if row['decision'] == 'quarantined' and row['order_present']),
        }
        return summary

    def close(self):
        self.conn.close()
