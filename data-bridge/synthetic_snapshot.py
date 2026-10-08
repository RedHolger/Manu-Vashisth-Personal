"""Canonical synthetic snapshot shared by the fault harness and its workers.

Both the clean run and the faulted run must import exactly this snapshot, so the
harness can compare the resulting logical datasets byte for byte.
"""
import json

from project import Source, digest

SNAPSHOT = 'synthetic-fault-matrix-v1'
SOURCE_NAME = 'faults'
PAGE_SIZE = 3
SCHEMA = 'a'

ROWS = [
    {'id': 'o01', 'customer': 'Alice', 'amount': '10.25'},
    {'id': 'o02', 'customer': 'Bob', 'amount': '2.00'},
    {'id': 'o03', 'customer': 'Cara', 'amount': '3.50'},
    {'bad': 'row'},                                        # schema drift
    {'id': 'o05', 'customer': 'Dan', 'amount': '4.00'},
    {'id': 'o01', 'customer': 'Zed', 'amount': '99.00'},   # conflicting duplicate
    {'id': 'o06', 'customer': 'Eve', 'amount': '5.25'},
    {'id': 'o07', 'customer': 'Fay', 'amount': '6.00'},
    {'id': 'o08', 'customer': 'Gil', 'amount': '7.00'},
    {'id': 'o09', 'customer': 'Hal', 'amount': '8.50'},
    {'id': 'o10', 'customer': 'Ivy', 'amount': '9.00'},
    {'id': 'o11', 'customer': 'Jan', 'amount': '11.00'},
]

EXPECTED_QUARANTINED = 2
EXPECTED_ORDERS = len(ROWS) - EXPECTED_QUARANTINED
CHECKSUM = digest(ROWS)


def build_source(snapshot=SNAPSHOT, page_size=PAGE_SIZE):
    return Source(list(ROWS), page_size=page_size, snapshot=snapshot)


def canonical(db, name):
    """The logical dataset an import produced, in a form two runs can compare."""
    orders = [{'id': row['id'], 'customer': row['customer'], 'cents': row['cents']}
              for row in db.conn.execute(
                  'SELECT id, customer, cents FROM orders WHERE source = %s'
                  ' ORDER BY id', (name,)).fetchall()]
    rows = [{'position': row['position'], 'origin_id': row['origin_id'],
             'decision': row['decision'], 'normalized_id': row['normalized_id'],
             'payload_sha256': row['payload_sha256']}
            for row in db.conn.execute(
                'SELECT position, origin_id, decision, normalized_id, payload_sha256'
                ' FROM raw WHERE source = %s ORDER BY position', (name,)).fetchall()]
    quarantine = [{'position': row['position'], 'reason': row['reason']}
                  for row in db.conn.execute(
                      'SELECT position, reason FROM quarantine WHERE source = %s'
                      ' ORDER BY position', (name,)).fetchall()]
    checkpoint = db.report(name)['checkpoint']
    db.conn.commit()   # reads must not leave an implicit transaction open
    return {
        'orders': orders,
        'rows': rows,
        'quarantine': quarantine,
        'checkpoint': {
            'seen': checkpoint['seen'] if checkpoint else None,
            'done': checkpoint['done'] if checkpoint else None,
            'snapshot': checkpoint['snapshot'] if checkpoint else None,
            'checksum': checkpoint['checksum'] if checkpoint else None,
        },
    }


def dataset_hash(dataset):
    payload = json.dumps(
        {'orders': dataset['orders'], 'rows': dataset['rows'],
         'quarantine': dataset['quarantine']},
        sort_keys=True, separators=(',', ':'))
    import hashlib
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
