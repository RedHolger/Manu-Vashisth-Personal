"""Worker for the P06-04 import evaluation: same kills, plus a fetch log.

Reuses the P06-03 self-killing importer unchanged and adds one thing the
evaluation needs — a record of every page actually fetched by this process, with
its cursor, byte size and duration, appended to a shared log file. Summing those
lines across processes gives repeated pages and repeated bytes for a resumable
run that was killed and restarted.
"""
import argparse
import json
import os
import signal
import sys
import time

from fault_worker import SelfKillingImporter
from pg_adapter import DEFAULT_DSN
from synthetic_snapshot import SCHEMA, SNAPSHOT, SOURCE_NAME, build_source


class RecordingSource:
    def __init__(self, inner, log_path, run_id, source_name):
        self.inner = inner
        self.log_path = log_path
        self.run_id = run_id
        self.source_name = source_name

    def fetch(self, cursor):
        started = time.perf_counter()
        page = self.inner.fetch(cursor)
        payload = json.dumps(page, sort_keys=True, separators=(',', ':'))
        entry = {
            'run': self.run_id,
            'source': self.source_name,
            'cursor': cursor,
            'next': page['next'],
            'start': page['start'],
            'rows': len(page['rows']),
            'bytes': len(payload.encode('utf-8')),
            'fetch_ms': round((time.perf_counter() - started) * 1000, 4),
            'pid': os.getpid(),
            'at': time.time(),
        }
        if self.log_path:
            with open(self.log_path, 'a', encoding='utf-8') as handle:
                handle.write(json.dumps(entry, sort_keys=True) + '\n')
        return page


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=DEFAULT_DSN)
    parser.add_argument('--source', default=SOURCE_NAME)
    parser.add_argument('--kill-after-rows', type=int, default=0)
    parser.add_argument('--kill-after-pages', type=int, default=0)
    parser.add_argument('--fetch-log', default=None)
    parser.add_argument('--run', default='run')
    parser.add_argument('--snapshot', default=None)
    args = parser.parse_args(argv)

    snapshot = args.snapshot or SNAPSHOT

    db = SelfKillingImporter(args.dsn, args.kill_after_rows)
    source = RecordingSource(build_source(snapshot=snapshot), args.fetch_log,
                             args.run, args.source)
    pages = 0
    while True:
        more = db.step(args.source, source, SCHEMA)
        pages += 1
        if args.kill_after_pages and pages >= args.kill_after_pages:
            sys.stdout.flush()
            os.kill(os.getpid(), signal.SIGKILL)
        if not more:
            break

    report = db.report(args.source)
    print(json.dumps({'pages': pages, 'rows_written': db.rows_written,
                      'report': report}, sort_keys=True))
    db.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
