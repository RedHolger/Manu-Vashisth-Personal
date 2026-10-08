"""P06-02 persistent adapter: one transaction per page, row-level completeness."""
import csv
import os
import tempfile
import unittest
from pathlib import Path

from fixture_server import Fixture, FixtureServer
from http_transport import HttpClient
from project import Source, digest

try:
    import psycopg
    from pg_adapter import DEFAULT_DSN, PgImporter
except Exception as _exc:  # pragma: no cover - exercised only without psycopg
    psycopg = None
    DEFAULT_DSN = str(_exc)
    PgImporter = None


def _database_available():
    if psycopg is None:
        return False
    try:
        with psycopg.connect(DEFAULT_DSN, connect_timeout=3) as conn:
            conn.execute('SELECT 1')
        return True
    except Exception:
        return False


AVAILABLE = _database_available()
SKIP_REASON = 'requires psycopg and a running P06 PostgreSQL (%s)' % DEFAULT_DSN

MIXED_ROWS = [
    {'id': 'a1', 'customer': 'Alice', 'amount': '10.25'},
    {'id': 'a2', 'customer': 'Bob', 'amount': '2.00'},
    {'bad': 'row'},
    {'id': 'a1', 'customer': 'Zed', 'amount': '99.00'},
    {'id': 'a5', 'customer': 'Eve', 'amount': '1.001'},
]
VALID_ROWS = [
    {'id': 'a1', 'customer': 'Alice', 'amount': '10.25'},
    {'id': 'a2', 'customer': 'Bob', 'amount': '2.00'},
    {'id': 'a3', 'customer': 'Cara', 'amount': '3.50'},
    {'id': 'a4', 'customer': 'Dan', 'amount': '4.00'},
    {'id': 'a5', 'customer': 'Eve', 'amount': '5.25'},
    {'id': 'a6', 'customer': 'Fay', 'amount': '6.00'},
]


@unittest.skipUnless(AVAILABLE, SKIP_REASON)
class PostgresAdapterBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = PgImporter()
        self.addCleanup(self.db.close)
        with self.db.conn.transaction():
            self.db.conn.execute('TRUNCATE runs, raw, orders, quarantine')

    def counts(self):
        out = {}
        for table in ('runs', 'raw', 'orders', 'quarantine'):
            out[table] = self.db.conn.execute(
                'SELECT COUNT(*) AS n FROM %s' % table).fetchone()['n']
        return out


class AtomicityTests(PostgresAdapterBase):
    def test_data_quarantine_and_checkpoint_commit_together(self):
        source = Source(MIXED_ROWS, page_size=len(MIXED_ROWS), snapshot='mixed-v1')

        self.db.step('mixed', source, 'a')

        self.assertEqual(self.counts(),
                         {'runs': 1, 'raw': 5, 'orders': 2, 'quarantine': 3})
        report = self.db.report('mixed')
        self.assertEqual(report['checkpoint']['seen'], 5)
        self.assertEqual(report['checkpoint']['done'], 1)
        self.assertEqual(report['checkpoint']['snapshot'], 'mixed-v1')
        self.assertEqual(report['valid_unique_orders'], 2)
        self.assertEqual([row['position'] for row in report['quarantine']],
                         [2, 3, 4])

    def test_crash_before_commit_leaves_no_rows_and_no_checkpoint(self):
        source = Source(MIXED_ROWS, page_size=len(MIXED_ROWS), snapshot='mixed-v1')

        with self.assertRaises(RuntimeError):
            self.db.step('mixed', source, 'a', fail_before_commit=True)

        self.assertEqual(self.counts(),
                         {'runs': 0, 'raw': 0, 'orders': 0, 'quarantine': 0})
        self.assertIsNone(self.db.report('mixed')['checkpoint'])

        self.db.step('mixed', source, 'a')

        self.assertEqual(self.counts(),
                         {'runs': 1, 'raw': 5, 'orders': 2, 'quarantine': 3})

    def test_checkpoint_only_reflects_committed_pages(self):
        source = Source(VALID_ROWS, page_size=2, snapshot='valid-v1')

        self.db.step('csv', source, 'a')
        self.assertEqual(self.counts(),
                         {'runs': 1, 'raw': 2, 'orders': 2, 'quarantine': 0})
        self.assertEqual(self.db.report('csv')['checkpoint']['seen'], 2)

        with self.assertRaises(RuntimeError):
            self.db.step('csv', source, 'a', fail_before_commit=True)

        self.assertEqual(self.counts(),
                         {'runs': 1, 'raw': 2, 'orders': 2, 'quarantine': 0})
        self.assertEqual(self.db.report('csv')['checkpoint']['seen'], 2)

        self.db.step('csv', source, 'a')

        self.assertEqual(self.counts(),
                         {'runs': 1, 'raw': 4, 'orders': 4, 'quarantine': 0})
        self.assertEqual(self.db.report('csv')['checkpoint']['seen'], 4)
        self.assertEqual(source.calls, 3)


class PersistenceContractTests(PostgresAdapterBase):
    def test_snapshot_checksum_and_original_identity_are_persisted(self):
        source = Source(MIXED_ROWS, page_size=len(MIXED_ROWS), snapshot='mixed-v1')

        self.db.step('mixed', source, 'a')

        checkpoint = self.db.report('mixed')['checkpoint']
        self.assertEqual(checkpoint['snapshot'], 'mixed-v1')
        self.assertEqual(checkpoint['checksum'], digest(source.rows))

        rows = {row['position']: row for row in self.db.completeness('mixed')}
        self.assertEqual(rows[0]['origin_id'], 'a1')
        self.assertEqual(rows[0]['normalized_id'], 'a1')
        self.assertEqual(rows[0]['decision'], 'normalized')
        self.assertIsNone(rows[2]['normalized_id'])
        self.assertEqual(rows[2]['decision'], 'quarantined')
        self.assertEqual(rows[2]['origin_id'], None)
        self.assertEqual(
            self.db.conn.execute(
                'SELECT reason FROM quarantine WHERE source = %s AND position = 2',
                ('mixed',)).fetchone()['reason'],
            'schema drift')
        for position, row in rows.items():
            self.assertEqual(len(row['payload_sha256']), 64)

    def test_schema_b_records_keep_their_source_identity(self):
        rows = [{'order_id': 'o1', 'buyer': 'Cara', 'total_cents': 900},
                {'order_id': 'o2', 'buyer': 'Dee', 'total_cents': 1000}]
        source = Source(rows, page_size=2, snapshot='b-v1')

        self.db.step('orders_b', source, 'b')

        completeness = self.db.completeness('orders_b')
        self.assertEqual([row['origin_id'] for row in completeness], ['o1', 'o2'])
        self.assertEqual([row['normalized_id'] for row in completeness], ['o1', 'o2'])
        self.assertEqual(
            self.db.report('orders_b')['valid_unique_orders'], 2)


class CompletenessExportTests(PostgresAdapterBase):
    def test_row_level_report_covers_every_source_position(self):
        source = Source(MIXED_ROWS, page_size=len(MIXED_ROWS), snapshot='mixed-v1')
        self.db.step('mixed', source, 'a')

        path = Path(self.tmp.name) / 'completeness.csv'
        summary = self.db.export_completeness('mixed', path)

        with open(path, newline='', encoding='utf-8') as handle:
            exported = list(csv.DictReader(handle))

        self.assertEqual(len(exported), len(MIXED_ROWS))
        self.assertEqual([row['position'] for row in exported],
                         [str(i) for i in range(len(MIXED_ROWS))])
        self.assertEqual([row['decision'] for row in exported],
                         ['normalized', 'normalized', 'quarantined',
                          'quarantined', 'quarantined'])
        self.assertEqual([row['order_present'] for row in exported],
                         ['true', 'true', 'false', 'true', 'false'])
        self.assertEqual(
            [row['reason'] for row in exported][2:],
            ['schema drift',
             'conflicting duplicate ID in immutable snapshot',
             'nonnegative 2-decimal amount required'])
        for row in exported:
            self.assertEqual(len(row['payload_sha256']), 64)

        self.assertEqual(summary, {
            'source': 'mixed',
            'positions': 5,
            'normalized': 2,
            'quarantined': 3,
            'distinct_orders': 2,
            'rows_with_order': 3,
            'normalized_without_order': 0,
            'quarantined_with_order': 1,
        })


@unittest.skipUnless(AVAILABLE, SKIP_REASON)
class HttpIntoPostgresTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = FixtureServer({
            'csv': Fixture(VALID_ROWS, snapshot='csv-snap-v1', page_size=2, fmt='csv'),
        }).start()
        self.addCleanup(self.server.stop)
        self.db = PgImporter()
        self.addCleanup(self.db.close)
        with self.db.conn.transaction():
            self.db.conn.execute('TRUNCATE runs, raw, orders, quarantine')

    def test_http_pages_land_in_postgres_with_a_complete_report(self):
        from connectors import CsvConnector
        client = HttpClient(self.server.base_url, timeout=1.0, max_retries=3,
                            backoff_base=0.01, sleep=lambda _: None)
        connector = CsvConnector(client, 'csv')
        while self.db.step('csv', connector, 'a'):
            pass

        report = self.db.report('csv')
        self.assertEqual(report['valid_unique_orders'], len(VALID_ROWS))
        self.assertEqual(report['checkpoint']['done'], 1)
        self.assertEqual(report['quarantine'], [])

        path = Path(self.tmp.name) / 'completeness.csv'
        summary = self.db.export_completeness('csv', path)
        self.assertEqual(summary['positions'], len(VALID_ROWS))
        self.assertEqual(summary['normalized'], len(VALID_ROWS))
        self.assertEqual(summary['normalized_without_order'], 0)
        self.assertEqual(self.server.count(), 3)


if __name__ == '__main__':
    unittest.main()
