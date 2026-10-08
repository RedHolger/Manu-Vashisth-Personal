"""P06-03 fault matrix: real process kills, adversarial sources, resumed equivalence.

Answers one acceptance question: does a resumed immutable snapshot produce the
same logical dataset as a clean run, with no silent truncated success?

Two things are compared:

- a *clean run* of the shared synthetic snapshot, and
- a *faulted run* of the same snapshot that is SIGKILLed twice — once inside an
  open page transaction (crash between write and checkpoint) and once right
  after a page commits — then resumed by fresh processes.

Every fault class in the matrix must end in either an explicit error or an
explicit quarantine decision, never in a checkpoint that claims success with
missing rows.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import psycopg

from pg_adapter import DEFAULT_DSN, PgImporter
from project import IntegrityError, Source
from synthetic_snapshot import (
    CHECKSUM, EXPECTED_ORDERS, EXPECTED_QUARANTINED, PAGE_SIZE, ROWS,
    SCHEMA, SOURCE_NAME, SNAPSHOT, build_source, canonical, dataset_hash)

HERE = Path(__file__).resolve().parent
WORKER = HERE / 'fault_worker.py'


def log(message):
    """Progress on stderr so stdout stays a single JSON document."""
    print(message, file=sys.stderr, flush=True)


def tx_status(db):
    return db.conn.info.transaction_status.name


# --- adversarial sources ---------------------------------------------------

class RepeatedCursorSource(Source):
    """Always advertises a cursor that points back at the current page."""

    def fetch(self, cursor):
        page = super().fetch(cursor)
        page['next'] = str(page['start'])
        return page


class MissingCursorSource(Source):
    """Skips ahead, so the requested cursor's page never arrives."""

    def fetch(self, cursor):
        page = super().fetch(cursor)
        page['start'] = int(page['start']) + len(page['rows'])
        return page


class TruncatedSource(Source):
    """Declares the end of the stream while rows are still outstanding."""

    def fetch(self, cursor):
        page = super().fetch(cursor)
        page['next'] = None
        return page


class ChangedContentSource(Source):
    """Edits a row on the final page without changing the advertised checksum."""

    def fetch(self, cursor):
        page = super().fetch(cursor)
        if page['next'] is None and page['rows']:
            rows = [dict(row) for row in page['rows']]
            rows[-1] = dict(rows[-1], amount='99.99')
            page['rows'] = rows
        return page


# --- helpers ---------------------------------------------------------------

def reset(db):
    with db.conn.transaction():
        db.conn.execute('TRUNCATE runs, raw, orders, quarantine')


def state(db, name):
    report = db.report(name)
    checkpoint = report['checkpoint']
    rows = db.conn.execute(
        'SELECT COUNT(*) AS n FROM raw WHERE source = %s',
        (name,)).fetchone()['n']
    db.conn.commit()   # every read must close the implicit transaction it opened,
                       # or the harness would hold locks while workers start
    return {
        'rows': rows,
        'orders': report['valid_unique_orders'],
        'quarantined': len(report['quarantine']),
        'seen': checkpoint['seen'] if checkpoint else None,
        'done': checkpoint['done'] if checkpoint else None,
    }


def wait_for_stale_backends(db, timeout=10.0):
    """Wait until a SIGKILLed worker's transaction has been cleaned up."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with db.conn.transaction():
            row = db.conn.execute(
                "SELECT count(*) AS n FROM pg_stat_activity"
                " WHERE pid <> pg_backend_pid() AND state = 'idle in transaction'"
                " AND datname = current_database()").fetchone()
        if row['n'] == 0:
            return True
        time.sleep(0.1)
    return False


def run_page(db, name, source, schema=SCHEMA, **kwargs):
    """One page step, returning its outcome instead of raising."""
    try:
        more = db.step(name, source, schema, **kwargs)
        return {'raised': None, 'more': more}
    except Exception as exc:  # noqa: BLE001 - the matrix records every failure class
        return {'raised': '%s: %s' % (type(exc).__name__, exc), 'more': False}


def worker(argv):
    result = subprocess.run(
        [sys.executable, str(WORKER)] + argv,
        capture_output=True, text=True, cwd=str(HERE))
    return {
        'argv': argv,
        'returncode': result.returncode,
        'killed_by_sigkill': result.returncode in (-9, 137),
        'stdout': result.stdout.strip(),
        'stderr': result.stderr.strip(),
    }


# --- the matrix ------------------------------------------------------------

def in_process_faults(db):
    scenarios = []

    def record(name, fault, outcome, error, extra=None):
        observed = state(db, name)
        # A run only "claims success" if it marked itself done; doing so while the
        # row counts disagree with the checkpoint is exactly a silent truncation.
        silent = observed['done'] == 1 and (
            observed['rows'] != observed['seen']
            or observed['orders'] + observed['quarantined'] != observed['rows'])
        entry = {'fault': fault, 'name': name, 'outcome': outcome, 'error': error,
                 'silent_truncated_success': silent, 'state': observed}
        entry.update(extra or {})
        scenarios.append(entry)

    # repeated cursor
    name = 'f_repeated_cursor'
    outcome = run_page(db, name, RepeatedCursorSource(ROWS, PAGE_SIZE, SNAPSHOT))
    record(name, 'repeated cursor (next points back at the page)',
           'explicit IntegrityError' if outcome['raised'] else 'ACCEPTED (wrong)',
           outcome['raised'])

    # missing cursor
    name = 'f_missing_cursor'
    outcome = run_page(db, name, MissingCursorSource(ROWS, PAGE_SIZE, SNAPSHOT))
    record(name, 'missing cursor (source skips a page)',
           'explicit IntegrityError' if outcome['raised'] else 'ACCEPTED (wrong)',
           outcome['raised'])

    # changed snapshot identity
    name = 'f_changed_snapshot'
    source = build_source()
    first = run_page(db, name, source)
    source.snapshot = SNAPSHOT + '-changed'
    second = run_page(db, name, source)
    record(name, 'changed snapshot identity mid-run',
           'explicit IntegrityError' if second['raised'] else 'ACCEPTED (wrong)',
           second['raised'] or ('first page: %s' % first['raised']),
           {'first_page_raised': first['raised']})

    # changed content under an unchanged checksum
    name = 'f_changed_content'
    source = ChangedContentSource(ROWS, PAGE_SIZE, SNAPSHOT)
    raised = None
    for _ in range(len(ROWS) + 2):   # walk to the final page, where the manifest is checked
        outcome = run_page(db, name, source)
        if outcome['raised']:
            raised = outcome['raised']
            break
        if not outcome['more']:
            break
    record(name, 'row edited under an immutable snapshot (checksum unchanged)',
           'explicit IntegrityError' if raised else 'ACCEPTED (wrong)',
           raised)

    # truncated stream
    name = 'f_truncated'
    outcome = run_page(db, name, TruncatedSource(ROWS, PAGE_SIZE, SNAPSHOT))
    record(name, 'truncated stream (end declared early)',
           'explicit IntegrityError' if outcome['raised'] else 'ACCEPTED (wrong)',
           outcome['raised'])

    # malformed row: not an object at all
    name = 'f_malformed_row'
    source = Source([[1, 2, 3], {'id': 'm1', 'customer': 'Ann', 'amount': '1.00'}],
                    page_size=2, snapshot=SNAPSHOT)
    run_page(db, name, source)
    reasons = [row['reason'] for row in db.report(name)['quarantine']]
    record(name, 'malformed row (payload is not an object)',
           'quarantined' if reasons else 'ACCEPTED (wrong)',
           reasons[0] if reasons else None)

    # schema drift: wrong key set
    name = 'f_schema_drift'
    source = Source([{'order_id': 'd1', 'buyer': 'Ann', 'total_cents': 100}],
                    page_size=1, snapshot=SNAPSHOT)
    run_page(db, name, source, schema='a')
    reasons = [row['reason'] for row in db.report(name)['quarantine']]
    record(name, 'schema drift (schema b record presented as schema a)',
           'quarantined' if reasons else 'ACCEPTED (wrong)',
           reasons[0] if reasons else None)

    # conflicting duplicate ids
    name = 'f_duplicate_id'
    source = Source([{'id': 'x1', 'customer': 'Ann', 'amount': '1.00'},
                     {'id': 'x1', 'customer': 'Bob', 'amount': '2.00'}],
                    page_size=2, snapshot=SNAPSHOT)
    run_page(db, name, source)
    report = db.report(name)
    reasons = [row['reason'] for row in report['quarantine']]
    record(name, 'conflicting duplicate ids in one immutable snapshot',
           'quarantined' if reasons else 'ACCEPTED (wrong)',
           reasons[0] if reasons else None,
           {'orders': report['valid_unique_orders']})

    return scenarios


def process_kill_runs(db, python=sys.executable):
    reset(db)
    observations = []

    log('  worker 1: SIGKILL mid-page')
    first = worker(['--dsn', DEFAULT_DSN, '--source', SOURCE_NAME,
                    '--kill-after-rows', '5'])
    log('  worker 1 rc=%s, waiting for cleanup' % first['returncode'])
    wait_for_stale_backends(db)
    first_state = state(db, SOURCE_NAME)
    observations.append({
        'kill': 'SIGKILL inside an open page transaction (after 5 rows written)',
        'worker': first,
        'observed': first_state,
        'note': 'page 1 was committed, page 2 rolled back entirely',
    })

    log('  worker 2: SIGKILL after page 2')
    second = worker(['--dsn', DEFAULT_DSN, '--source', SOURCE_NAME,
                     '--kill-after-pages', '1'])
    log('  worker 2 rc=%s, waiting for cleanup' % second['returncode'])
    wait_for_stale_backends(db)
    second_state = state(db, SOURCE_NAME)
    observations.append({
        'kill': 'SIGKILL immediately after a page commits (page 2)',
        'worker': second,
        'observed': second_state,
        'note': 'checkpoint advanced to seen 6; pages 3 and 4 never started',
    })

    log('  worker 3: resume to completion')
    third = worker(['--dsn', DEFAULT_DSN, '--source', SOURCE_NAME])
    log('  worker 3 rc=%s' % third['returncode'])
    wait_for_stale_backends(db)
    third_state = state(db, SOURCE_NAME)
    observations.append({
        'kill': 'no kill — fresh process resumes from the surviving checkpoint',
        'worker': third,
        'observed': third_state,
        'note': 'import runs to completion from cursor 6',
    })

    return observations, [first['returncode'], second['returncode'],
                          third['returncode']]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=DEFAULT_DSN)
    options = parser.parse_args(argv)

    out = {'card': 'P06-03', 'dsn': options.dsn,
           'snapshot': SNAPSHOT, 'checksum': CHECKSUM,
           'rows': len(ROWS), 'page_size': PAGE_SIZE,
           'expected_orders': EXPECTED_ORDERS,
           'expected_quarantined': EXPECTED_QUARANTINED}
    checks = {}

    db = PgImporter(options.dsn)
    try:
        log('connected (%s)' % tx_status(db))
        reset(db)
        log('clean run starting (%s)' % tx_status(db))

        # 1. clean run of the shared snapshot
        clean_name = 'clean_run'
        clean_source = build_source()
        while db.step(clean_name, clean_source, SCHEMA):
            pass
        clean = canonical(db, clean_name)
        log('clean run done: %s (%s)' % (state(db, clean_name), tx_status(db)))
        out['clean_run'] = {'dataset_hash': dataset_hash(clean),
                            'state': state(db, clean_name),
                            'checkpoint': clean['checkpoint']}

        # 2. fault matrix, in process
        out['fault_matrix'] = in_process_faults(db)
        log('fault matrix done: %d scenarios (%s)'
            % (len(out['fault_matrix']), tx_status(db)))

        # 3. faulted run with real SIGKILLs, then resume
        log('process kill run starting (%s)' % tx_status(db))
        kills, returncodes = process_kill_runs(db)
        out['process_kills'] = kills
        faulted = canonical(db, SOURCE_NAME)
        log('faulted run done: %s (%s)' % (state(db, SOURCE_NAME), tx_status(db)))
        out['faulted_run'] = {'dataset_hash': dataset_hash(faulted),
                              'state': state(db, SOURCE_NAME),
                              'checkpoint': faulted['checkpoint']}

        # 4. the acceptance comparison
        out['clean_dataset'] = {'orders': clean['orders'],
                                'quarantine': clean['quarantine']}
        out['faulted_dataset'] = {'orders': faulted['orders'],
                                  'quarantine': faulted['quarantine']}
        out['datasets_identical'] = clean == faulted

        # --- checks -------------------------------------------------------
        checks['clean_run_complete'] = (
            out['clean_run']['state'] == {
                'rows': len(ROWS), 'orders': EXPECTED_ORDERS,
                'quarantined': EXPECTED_QUARANTINED,
                'seen': len(ROWS), 'done': 1})
        checks['kill_inside_transaction_rolls_back_the_page'] = (
            kills[0]['observed']['rows'] == PAGE_SIZE
            and kills[0]['observed']['seen'] == PAGE_SIZE
            and kills[0]['observed']['done'] == 0)
        checks['kill_after_commit_keeps_that_page'] = (
            kills[1]['observed']['rows'] == PAGE_SIZE * 2
            and kills[1]['observed']['seen'] == PAGE_SIZE * 2
            and kills[1]['observed']['done'] == 0)
        checks['workers_really_were_killed'] = (
            returncodes[0] in (-9, 137) and returncodes[1] in (-9, 137)
            and returncodes[2] == 0)
        checks['resume_reaches_completion'] = (
            kills[2]['observed']['rows'] == len(ROWS)
            and kills[2]['observed']['seen'] == len(ROWS)
            and kills[2]['observed']['done'] == 1)
        checks['resumed_dataset_equals_clean_run'] = (
            out['clean_run']['dataset_hash'] == out['faulted_run']['dataset_hash']
            and out['datasets_identical'])

        rejected = [entry for entry in out['fault_matrix']
                    if entry['error'] and 'IntegrityError' in str(entry['error'])]
        checks['all_integrity_faults_rejected_explicitly'] = len(rejected) == 5
        quarantined = [entry for entry in out['fault_matrix']
                       if entry['outcome'] == 'quarantined']
        checks['all_row_faults_quarantined'] = len(quarantined) == 3
        checks['no_silent_truncated_success'] = all(
            not entry['silent_truncated_success'] for entry in out['fault_matrix'])
        observed_states = [entry['state'] for entry in out['fault_matrix']]
        observed_states += [item['observed'] for item in kills]
        observed_states += [out['clean_run']['state'], out['faulted_run']['state']]
        checks['checkpoint_never_runs_ahead_of_the_rows_written'] = all(
            item['seen'] is None or item['seen'] == item['rows']
            for item in observed_states)
    finally:
        db.close()

    out['checks'] = checks
    out['checks_met'] = sum(1 for value in checks.values() if value)
    out['checks_total'] = len(checks)
    out['all_met'] = all(checks.values())
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['all_met'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
