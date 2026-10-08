"""Two connectors (CSV and JSON) exposing the reference ``Source.fetch`` contract.

Each connector performs one logical page fetch.  Transient upstream failures are
retried inside the transport against the same cursor; a permanent failure is
raised as ``PermanentError`` so the importer can fail explicitly instead of
recording a partial page.
"""
import csv
import io
import json

from http_transport import PermanentError

CSV_META = ('x-snapshot', 'x-start', 'x-next', 'x-total', 'x-checksum')
JSON_KEYS = ('snapshot', 'start', 'rows', 'next', 'total', 'checksum')


def _int_or_none(value, header, permanent):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise permanent('%s is not an integer: %r' % (header, value))


class BaseConnector:
    format = None

    def __init__(self, client, dataset, name=None):
        self.client = client
        self.dataset = dataset
        self.name = name or dataset

    def fetch(self, cursor):
        response = self.client.get(
            '/%s/page' % self.dataset, {'cursor': cursor or '0', 'format': self.format})
        return self.parse(response)

    def parse(self, response):
        raise NotImplementedError


class CsvConnector(BaseConnector):
    """CSV payload: page metadata travels in response headers."""

    format = 'csv'

    def parse(self, response):
        def permanent(message):
            return PermanentError('%s: %s' % (self.dataset, message))

        headers = response.headers
        missing = [name for name in CSV_META[:2] + CSV_META[3:] if name not in headers]
        if missing:
            raise permanent('missing metadata header(s): %s' % ', '.join(missing))

        try:
            text = response.body.decode('utf-8')
        except UnicodeDecodeError as err:
            raise permanent('page body is not utf-8: %s' % err)
        rows = list(csv.DictReader(io.StringIO(text)))

        start = _int_or_none(headers.get('x-start'), 'x-start', permanent)
        total = _int_or_none(headers.get('x-total'), 'x-total', permanent)
        if start is None or total is None:
            raise permanent('x-start and x-total are required')
        nxt = headers.get('x-next')
        if nxt == '':
            nxt = None
        return {
            'snapshot': headers.get('x-snapshot'),
            'start': start,
            'rows': rows,
            'next': nxt,
            'total': total,
            'checksum': headers.get('x-checksum'),
        }


class JsonConnector(BaseConnector):
    """JSON payload: the response body is the page envelope itself."""

    format = 'json'

    def parse(self, response):
        def permanent(message):
            return PermanentError('%s: %s' % (self.dataset, message))

        try:
            page = json.loads(response.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as err:
            raise permanent('page body is not valid JSON: %s' % err)
        if not isinstance(page, dict):
            raise permanent('page body must be a JSON object, got %s' % type(page).__name__)
        absent = [key for key in JSON_KEYS if key not in page]
        if absent:
            raise permanent('page envelope missing key(s): %s' % ', '.join(absent))
        if not isinstance(page['rows'], list):
            raise permanent('rows must be a list')
        if not isinstance(page['start'], int) or not isinstance(page['total'], int):
            raise permanent('start and total must be integers')
        if page['next'] is not None and not isinstance(page['next'], str):
            raise permanent('next must be a string cursor or null')
        if not isinstance(page['snapshot'], str) or not page['snapshot']:
            raise permanent('snapshot must be a non-empty string')
        return {key: page[key] for key in JSON_KEYS}
