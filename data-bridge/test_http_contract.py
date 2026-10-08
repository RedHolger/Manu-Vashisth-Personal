"""P06-01 HTTP connector contract: retry semantics, permanent failures, timeout."""
import tempfile
import unittest
from pathlib import Path

from connectors import CsvConnector, JsonConnector
from fixture_server import Fixture, FixtureServer
from http_transport import HttpClient, PermanentError, retry_after_seconds
from project import Importer, TransientError

CSV_ROWS = [
    {'id': 'a1', 'customer': 'Alice', 'amount': '10.25'},
    {'id': 'a2', 'customer': 'Bob', 'amount': '2.00'},
    {'id': 'a3', 'customer': 'Cara', 'amount': '3.50'},
    {'id': 'a4', 'customer': 'Dan', 'amount': '4.00'},
    {'id': 'a5', 'customer': 'Eve', 'amount': '5.25'},
    {'id': 'a6', 'customer': 'Fay', 'amount': '6.00'},
]
JSON_ROWS = [
    {'order_id': 'o1', 'buyer': 'Cara', 'total_cents': 900},
    {'order_id': 'o2', 'buyer': 'Dee', 'total_cents': 1000},
    {'order_id': 'o3', 'buyer': 'Eli', 'total_cents': 1150},
    {'order_id': 'o4', 'buyer': 'Fay', 'total_cents': 1200},
]
TIMEOUT = 0.2
MAX_RETRIES = 3


class HttpContractBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = FixtureServer({
            'csv': Fixture(CSV_ROWS, snapshot='csv-snap-v1', page_size=2, fmt='csv'),
            'json': Fixture(JSON_ROWS, snapshot='json-snap-v1', page_size=2, fmt='json'),
        }).start()
        self.addCleanup(self.server.stop)
        self.client = HttpClient(
            self.server.base_url, timeout=TIMEOUT, max_retries=MAX_RETRIES,
            backoff_base=0.01, max_retry_after=0.2, sleep=lambda _: None)
        self.db = Importer(Path(self.tmp.name) / 'import.sqlite')
        self.addCleanup(self.db.close)

    def import_all(self, name, connector, schema):
        while self.db.step(name, connector, schema):
            pass
        return self.db.report(name)


class HappyPathTests(HttpContractBase):
    def test_csv_connector_imports_every_page(self):
        report = self.import_all('csv', CsvConnector(self.client, 'csv'), 'a')
        self.assertEqual(report['valid_unique_orders'], len(CSV_ROWS))
        self.assertEqual(report['checkpoint']['done'], 1)
        self.assertEqual(report['checkpoint']['seen'], len(CSV_ROWS))
        self.assertEqual(report['quarantine'], [])
        self.assertEqual(self.server.count(), 3)
        self.assertEqual(self.server.statuses(), [200, 200, 200])

    def test_json_connector_imports_every_page(self):
        report = self.import_all('json', JsonConnector(self.client, 'json'), 'b')
        self.assertEqual(report['valid_unique_orders'], len(JSON_ROWS))
        self.assertEqual(report['checkpoint']['done'], 1)
        self.assertEqual(report['checkpoint']['seen'], len(JSON_ROWS))
        self.assertEqual(self.server.count(), 2)
        self.assertEqual(self.server.statuses(), [200, 200])


class RetryTests(HttpContractBase):
    def test_429_retries_the_same_cursor_without_advancing(self):
        self.server.inject('csv', '0', 429, retry_after='0.01', times=2)
        connector = CsvConnector(self.client, 'csv')

        page = connector.fetch('0')

        self.assertEqual(page['start'], 0)
        self.assertEqual(self.server.cursors(), ['0', '0', '0'])
        self.assertEqual(self.server.statuses(), [429, 429, 200])
        self.assertIsNone(self.db.report('csv')['checkpoint'])

    def test_500_retries_the_same_cursor_without_advancing(self):
        self.server.inject('json', '0', 500, times=1)
        connector = JsonConnector(self.client, 'json')

        page = connector.fetch('0')

        self.assertEqual(page['start'], 0)
        self.assertEqual(self.server.cursors(), ['0', '0'])
        self.assertEqual(self.server.statuses(), [500, 200])
        self.assertIsNone(self.db.report('json')['checkpoint'])

    def test_transient_faults_import_one_page_per_cursor(self):
        self.server.inject('csv', '0', 429, retry_after='0.01', times=2)
        self.server.inject('csv', '2', 500, times=1)
        self.server.inject('csv', '4', 500, times=1)

        report = self.import_all('csv', CsvConnector(self.client, 'csv'), 'a')

        self.assertEqual(self.server.count(), 3 + 2 + 2)
        self.assertEqual(report['checkpoint']['done'], 1)
        self.assertEqual(report['checkpoint']['seen'], len(CSV_ROWS))
        self.assertEqual(report['valid_unique_orders'], len(CSV_ROWS))
        self.assertEqual(report['quarantine'], [])

    def test_retry_cap_exhausted_raises_transient_and_leaves_checkpoint(self):
        self.server.inject('csv', '0', 500, times=MAX_RETRIES + 1)
        connector = CsvConnector(self.client, 'csv')

        with self.assertRaises(TransientError):
            self.db.step('csv', connector, 'a')

        self.assertEqual(self.server.count(), MAX_RETRIES + 1)
        self.assertIsNone(self.db.report('csv')['checkpoint'])


class PermanentFailureTests(HttpContractBase):
    def test_permanent_http_status_fails_without_retry(self):
        self.server.inject('csv', '0', 400)
        connector = CsvConnector(self.client, 'csv')

        with self.assertRaises(PermanentError):
            self.db.step('csv', connector, 'a')

        self.assertEqual(self.server.count(), 1)
        self.assertIsNone(self.db.report('csv')['checkpoint'])

    def test_invalid_body_fails_without_retry(self):
        self.server.inject('json', '0', 200, body=b'<html>not a page</html>')
        connector = JsonConnector(self.client, 'json')

        with self.assertRaises(PermanentError) as ctx:
            self.db.step('json', connector, 'b')

        self.assertIn('not valid JSON', str(ctx.exception))
        self.assertEqual(self.server.count(), 1)
        self.assertIsNone(self.db.report('json')['checkpoint'])

    def test_missing_metadata_headers_fail_without_retry(self):
        self.server.inject('csv', '0', 200, body=b'id,customer,amount\n')
        connector = CsvConnector(self.client, 'csv')

        with self.assertRaises(PermanentError) as ctx:
            self.db.step('csv', connector, 'a')

        self.assertIn('missing metadata header', str(ctx.exception))
        self.assertEqual(self.server.count(), 1)


class TimeoutTests(HttpContractBase):
    def test_timeout_is_retried_then_succeeds(self):
        self.server.inject('csv', '0', 200, hang=TIMEOUT * 4, times=1)
        connector = CsvConnector(self.client, 'csv')

        page = connector.fetch('0')

        self.assertEqual(page['start'], 0)
        self.assertEqual(self.server.count(), 2)
        self.assertEqual(self.server.cursors(), ['0', '0'])

    def test_timeout_cap_exhausted_raises_transient(self):
        self.server.inject('csv', '0', 200, hang=TIMEOUT * 4, times=MAX_RETRIES + 1)
        connector = CsvConnector(self.client, 'csv')

        with self.assertRaises(TransientError):
            connector.fetch('0')

        self.assertEqual(self.server.count(), MAX_RETRIES + 1)


class RetryAfterParsingTests(unittest.TestCase):
    def test_delta_seconds(self):
        self.assertEqual(retry_after_seconds('0.5'), 0.5)
        self.assertEqual(retry_after_seconds(' 3 '), 3.0)
        self.assertEqual(retry_after_seconds('-1'), 0.0)

    def test_http_date(self):
        now = 1_700_000_000.0
        value = retry_after_seconds('Wed, 15 Nov 2023 22:08:00 GMT', now=now)
        self.assertAlmostEqual(value, 86080.0, delta=1.0)
        self.assertEqual(retry_after_seconds('garbage'), None)
        self.assertEqual(retry_after_seconds(None), None)


if __name__ == '__main__':
    unittest.main()
