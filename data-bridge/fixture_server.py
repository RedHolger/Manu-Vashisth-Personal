"""Local paginated HTTP fixture with scripted fault injection.

Serves immutable snapshot pages for a CSV dataset and a JSON dataset, and can
inject transient faults (429 with Retry-After, 500), permanent faults (400, or a
200 with an unparsable body) and stalls that exceed the client timeout.  Every
request is recorded so tests can assert which cursor the client retried.
"""
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from project import digest


class Fixture:
    def __init__(self, rows, snapshot='fixture-v1', page_size=2, fmt='json'):
        if page_size < 1:
            raise ValueError('positive page size')
        self.rows = rows
        self.snapshot = snapshot
        self.page_size = page_size
        self.format = fmt
        self.checksum = digest(rows)

    def page(self, cursor):
        start = int(cursor or 0)
        rows = self.rows[start:start + self.page_size]
        end = start + len(rows)
        return {
            'snapshot': self.snapshot,
            'start': start,
            'rows': rows,
            'next': str(end) if end < len(self.rows) else None,
            'total': len(self.rows),
            'checksum': self.checksum,
        }


class Fault:
    def __init__(self, dataset, cursor, status, retry_after=None, body=None,
                 hang=None, times=1):
        self.dataset = dataset
        self.cursor = cursor
        self.status = status
        self.retry_after = retry_after
        self.body = body
        self.hang = hang
        self.times = times


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        server = self.server
        parsed = urllib.parse.urlparse(self.path)
        parts = [part for part in parsed.path.split('/') if part]
        query = {key: value[0] for key, value in urllib.parse.parse_qs(
            parsed.query, keep_blank_values=True).items()}
        dataset_name = parts[0] if parts else ''
        cursor = query.get('cursor', '0')
        fmt = query.get('format', 'json')
        entry = server.record(dataset_name, cursor, fmt)
        if len(parts) != 2 or parts[1] != 'page':
            entry['status'] = 404
            self._respond(404, b'{"error":"unknown path"}', 'application/json')
            return
        if dataset_name not in server.datasets:
            entry['status'] = 404
            self._respond(404, b'{"error":"unknown dataset"}', 'application/json')
            return

        fault = server.take_fault(dataset_name, cursor)
        if fault is not None and fault.hang:
            time.sleep(fault.hang)
        if fault is not None and fault.body is not None:
            entry['status'] = fault.status
            self._respond(fault.status, fault.body, 'application/json')
            return
        if fault is not None:
            entry['status'] = fault.status
            headers = {}
            if fault.retry_after is not None:
                headers['Retry-After'] = str(fault.retry_after)
            self._respond(fault.status, b'{"error":"injected"}',
                          'application/json', headers)
            return

        fixture = server.datasets[dataset_name]
        page = fixture.page(cursor)
        if fmt == 'csv':
            body = _encode_csv(page['rows']).encode('utf-8')
            headers = {
                'X-Snapshot': page['snapshot'],
                'X-Start': str(page['start']),
                'X-Total': str(page['total']),
                'X-Checksum': page['checksum'],
            }
            if page['next'] is not None:
                headers['X-Next'] = page['next']
            entry['status'] = 200
            self._respond(200, body, 'text/csv', headers)
        else:
            entry['status'] = 200
            self._respond(200, json.dumps(page, sort_keys=True).encode('utf-8'),
                          'application/json')

    def _respond(self, status, body, content_type, headers=None):
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        self.server.lines.append(fmt % args)

    def handle(self):
        try:
            BaseHTTPRequestHandler.handle(self)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass


def _encode_csv(rows):
    import csv
    import io
    if not rows:
        return ''
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


class FixtureServer:
    def __init__(self, datasets=None, host='127.0.0.1', port=0):
        self.datasets = datasets or {}
        self._faults = []
        self.log = []
        self.lines = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer((host, port), _Handler)
        self._server.datasets = self.datasets
        self._server.take_fault = self._take_fault
        self._server.record = self._record
        self._server.lines = self.lines
        self._server.handle_error = lambda *args: None
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self):
        host, port = self._server.server_address[:2]
        return 'http://%s:%d' % (host, port)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    def inject(self, dataset, cursor, status, retry_after=None, body=None,
               hang=None, times=1):
        with self._lock:
            self._faults.append(Fault(dataset, cursor, status, retry_after,
                                      body, hang, times))

    def _take_fault(self, dataset, cursor):
        with self._lock:
            for fault in self._faults:
                if fault.dataset == dataset and fault.times > 0 and (
                        fault.cursor is None or fault.cursor == cursor):
                    fault.times -= 1
                    return fault
        return None

    def _record(self, dataset, cursor, fmt):
        with self._lock:
            entry = {'dataset': dataset, 'cursor': cursor, 'format': fmt,
                     'status': None, 'at': time.time()}
            self.log.append(entry)
            return entry

    def statuses(self):
        with self._lock:
            return [entry['status'] for entry in self.log
                    if entry['status'] is not None]

    def cursors(self):
        with self._lock:
            return [entry['cursor'] for entry in self.log]

    def count(self):
        with self._lock:
            return len(self.log)
