"""Child process for the P06-03 fault matrix: import a snapshot, then die hard.

Runs the shared synthetic snapshot through the PostgreSQL adapter and can kill
its own process with SIGKILL at two points that matter:

- ``--kill-after-rows N``   inside an open transaction, after N rows have been
  written and *before* the page commits (crash between write and checkpoint);
- ``--kill-after-pages N``  immediately after the Nth page has committed.

Either way the parent observes the database afterwards, restarts a worker, and
the run is resumed from whatever checkpoint actually survived.
"""
import argparse
import json
import os
import signal
import sys

from pg_adapter import DEFAULT_DSN, PgImporter
from synthetic_snapshot import SCHEMA, SOURCE_NAME, build_source


class SelfKillingImporter(PgImporter):
    """PgImporter that terminates the OS process inside the page transaction."""

    def __init__(self, dsn, kill_after_rows=0):
        super().__init__(dsn)
        self.rows_written = 0
        self.kill_after_rows = kill_after_rows

    def _record_row(self, *args, **kwargs):
        super()._record_row(*args, **kwargs)
        self.rows_written += 1
        if self.kill_after_rows and self.rows_written >= self.kill_after_rows:
            sys.stdout.flush()
            os.kill(os.getpid(), signal.SIGKILL)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=DEFAULT_DSN)
    parser.add_argument('--source', default=SOURCE_NAME)
    parser.add_argument('--kill-after-rows', type=int, default=0)
    parser.add_argument('--kill-after-pages', type=int, default=0)
    parser.add_argument('--snapshot', default=None)
    args = parser.parse_args(argv)

    from synthetic_snapshot import SNAPSHOT
    snapshot = args.snapshot or SNAPSHOT

    db = SelfKillingImporter(args.dsn, args.kill_after_rows)
    source = build_source(snapshot=snapshot)
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
