"""P06-04 import evaluation: one-shot versus resumable on the same source.

Runs the identical synthetic snapshot, page size and fault schedule through two
import strategies and reports what resumability costs and what it saves:

- **one-shot** — three attempts against the same two SIGKILLs, but a killed
  attempt discards the partial import and the next attempt starts again from
  row zero, re-fetching every page;
- **resumable** — the same three attempts and the same two SIGKILLs, but the
  next process continues from whatever checkpoint the killed one left behind.

Measured for both: missing rows, duplicate rows, pages fetched (and how many of
them were repeats), bytes fetched (and how many were repeats), rows discarded by
a restart, elapsed wall time and elapsed recovery after the first kill. Every
failed worker or divergent dataset is archived in ``failures``.
"""
import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psycopg

from pg_adapter import DEFAULT_DSN, PgImporter
from synthetic_snapshot import (
    PAGE_SIZE, ROWS, SCHEMA, SNAPSHOT, canonical, dataset_hash)

HERE = Path(__file__).resolve().parent
WORKER = HERE / 'eval_worker.py'
EXPECTED_POSITIONS = set(range(len(ROWS)))


def log(message):
    print(message, file=sys.stderr, flush=True)


def run_worker(argv):
    started = time.perf_counter()
    result = subprocess.run([sys.executable, str(WORKER)] + argv,
                            capture_output=True, text=True, cwd=str(HERE))
    return {
        'argv': argv,
        'returncode': result.returncode,
        'killed_by_sigkill': result.returncode in (-9, 137),
        'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
        'stdout': result.stdout.strip(),
        'stderr': result.stderr.strip(),
    }


def reset(db):
    with db.conn.transaction():
        db.conn.execute('TRUNCATE runs, raw, orders, quarantine')


def state(db, name):
    report = db.report(name)
    checkpoint = report['checkpoint']
    rows = db.conn.execute(
        'SELECT COUNT(*) AS n FROM raw WHERE source = %s',
        (name,)).fetchone()['n']
    db.conn.commit()
    return {
        'rows': rows,
        'orders': report['valid_unique_orders'],
        'quarantined': len(report['quarantine']),
        'seen': checkpoint['seen'] if checkpoint else None,
        'done': checkpoint['done'] if checkpoint else None,
    }


def fetch_metrics(log_path, run_id):
    entries = []
    with open(log_path, encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                entry = json.loads(line)
                if entry['run'] == run_id:
                    entries.append(entry)
    by_cursor = {}
    for entry in entries:
        by_cursor.setdefault(entry['cursor'], entry)
    return {
        'fetches': len(entries),
        'distinct_pages': len(by_cursor),
        'repeated_pages': len(entries) - len(by_cursor),
        'bytes_fetched': sum(entry['bytes'] for entry in entries),
        'bytes_distinct': sum(entry['bytes'] for entry in by_cursor.values()),
        'repeated_bytes': sum(entry['bytes'] for entry in entries)
                          - sum(entry['bytes'] for entry in by_cursor.values()),
        'rows_fetched': sum(entry['rows'] for entry in entries),
        'cursor_sequence': [entry['cursor'] for entry in entries],
    }


def row_metrics(db, name, dataset):
    observed = {row['position'] for row in dataset['rows']}
    return {
        'missing_rows': sorted(EXPECTED_POSITIONS - observed),
        'missing_row_count': len(EXPECTED_POSITIONS - observed),
        'unexpected_rows': sorted(observed - EXPECTED_POSITIONS),
        'duplicate_row_count': len(dataset['rows']) - len(observed),
        'duplicate_order_count': len(dataset['orders'])
                                 - len({row['id'] for row in dataset['orders']}),
        'state': state(db, name),
    }


def clear(db, name):
    with db.conn.transaction():
        for table in ('orders', 'quarantine', 'raw', 'runs'):
            db.conn.execute('DELETE FROM %s WHERE source = %%s' % table,
                            (name,))


def count_rows(db, name):
    rows = db.conn.execute(
        'SELECT COUNT(*) AS n FROM raw WHERE source = %s',
        (name,)).fetchone()['n']
    db.conn.commit()
    return rows


def run_attempts(db, name, run_id, fetch_log, wipe_between):
    """The identical fault schedule for both strategies.

    Three attempts: SIGKILL inside an open page transaction after five rows are
    written, SIGKILL immediately after the first page commits, then a clean run.
    What differs is what a restart means. ``wipe_between`` (one-shot) discards
    the partial import before every attempt, so the run starts again from row
    zero and re-fetches everything; without it (resumable) the next process
    continues from whatever checkpoint the killed process left behind.
    """
    workers = []
    after_first_kill = None
    discarded_rows = 0
    tails = (['--kill-after-rows', '5'], ['--kill-after-pages', '1'], [])
    for attempt, tail in enumerate(tails):
        if wipe_between:
            if attempt:
                discarded_rows += count_rows(db, name)
            clear(db, name)
        worker = run_worker(['--dsn', DEFAULT_DSN, '--source', name,
                             '--fetch-log', str(fetch_log), '--run', run_id]
                            + tail)
        workers.append(worker)
        if attempt == 0:
            after_first_kill = time.perf_counter()
    return workers, after_first_kill, discarded_rows


def one_shot(db, run_id, fetch_log):
    name = run_id.replace('one_shot_', 'oneshot_')
    started = time.perf_counter()
    workers, after_kill, discarded = run_attempts(
        db, name, run_id, fetch_log, wipe_between=True)
    finished = time.perf_counter()
    dataset = canonical(db, name)
    metrics = row_metrics(db, name, dataset)
    return {
        'run': run_id,
        'strategy': 'one-shot',
        'elapsed_ms': round((finished - started) * 1000, 3),
        'recovery_ms': round((finished - after_kill) * 1000, 3),
        'workers': workers,
        'kill_returncodes': [worker['returncode'] for worker in workers],
        'discarded_rows': discarded,
        'fetches': fetch_metrics(fetch_log, run_id),
        'state': metrics['state'],
        'missing_row_count': metrics['missing_row_count'],
        'missing_rows': metrics['missing_rows'],
        'duplicate_row_count': metrics['duplicate_row_count'],
        'duplicate_order_count': metrics['duplicate_order_count'],
        'dataset_hash': dataset_hash(dataset),
        'checkpoint': dataset['checkpoint'],
    }


def resumable(db, run_id, fetch_log):
    name = run_id
    started = time.perf_counter()
    workers, after_kill, discarded = run_attempts(
        db, name, run_id, fetch_log, wipe_between=False)
    finished = time.perf_counter()
    dataset = canonical(db, name)
    metrics = row_metrics(db, name, dataset)
    return {
        'run': run_id,
        'strategy': 'resumable',
        'elapsed_ms': round((finished - started) * 1000, 3),
        'recovery_ms': round((finished - after_kill) * 1000, 3),
        'workers': workers,
        'kill_returncodes': [worker['returncode'] for worker in workers],
        'discarded_rows': discarded,
        'fetches': fetch_metrics(fetch_log, run_id),
        'state': metrics['state'],
        'missing_row_count': metrics['missing_row_count'],
        'missing_rows': metrics['missing_rows'],
        'duplicate_row_count': metrics['duplicate_row_count'],
        'duplicate_order_count': metrics['duplicate_order_count'],
        'dataset_hash': dataset_hash(dataset),
        'checkpoint': dataset['checkpoint'],
    }


def summarise(runs, key):
    values = [run[key] for run in runs if run.get(key) is not None]
    if not values:
        return None
    return {'min': min(values), 'median': statistics.median(values),
            'max': max(values), 'samples': len(values)}


def totals(runs, keys):
    return {key: sum(run['fetches'][key] for run in runs) for key in keys}


def collect_failures(one, resu, expected_hash):
    failures = []

    def check(run, condition, detail):
        if not condition:
            failures.append({'run': run['run'], 'strategy': run['strategy'],
                             'detail': detail})

    for run in one + resu:
        check(run, run['missing_row_count'] == 0,
              'missing rows: %s' % run['missing_rows'])
        check(run, run['duplicate_row_count'] == 0
              and run['duplicate_order_count'] == 0,
              'duplicate rows/orders')
        check(run, run['state']['done'] == 1 and run['state']['rows'] == len(ROWS),
              'import did not complete: %s' % run['state'])
        check(run, run['dataset_hash'] == expected_hash,
              'dataset differs from the reference run')
        check(run, run['kill_returncodes'] == [-9, -9, 0],
              'unexpected worker exit codes: %s' % run['kill_returncodes'])
        check(run, all(not worker['stderr'] for worker in run['workers']),
              'a worker wrote to stderr: %r'
              % next((w['stderr'] for w in run['workers'] if w['stderr']), '')[:200])

    for run in one:
        check(run, run['discarded_rows'] > 0,
              'one-shot never discarded partial progress, so no restart happened')

    for run in resu:
        check(run, run['discarded_rows'] == 0,
              'resumable discarded %d rows, but it must keep its checkpoint'
              % run['discarded_rows'])

    return failures


def compare(one, resu, fetch_keys):
    block = {}
    for label, runs in (('one_shot', one), ('resumable', resu)):
        block[label] = {
            'elapsed_ms': summarise(runs, 'elapsed_ms'),
            'recovery_ms': summarise(runs, 'recovery_ms'),
            'totals': totals(runs, fetch_keys),
            'missing_row_count': sum(r['missing_row_count'] for r in runs),
            'duplicate_row_count': sum(r['duplicate_row_count'] for r in runs),
            'duplicate_order_count': sum(r['duplicate_order_count'] for r in runs),
            'discarded_rows': sum(r['discarded_rows'] for r in runs),
        }
    one_median = block['one_shot']['elapsed_ms']['median']
    resu_median = block['resumable']['elapsed_ms']['median']
    block['elapsed_overhead_ratio'] = (
        round(resu_median / one_median, 4) if one_median else None)
    return block


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=DEFAULT_DSN)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--out', default=None,
                        help='directory for fetch-log.jsonl and failures.json')
    options = parser.parse_args(argv)

    out = {'card': 'P06-04', 'dsn': options.dsn, 'snapshot': SNAPSHOT,
           'rows': len(ROWS), 'page_size': PAGE_SIZE, 'repeats': options.repeats}
    checks = {}

    with tempfile.TemporaryDirectory() as tmp:
        fetch_log = Path(tmp) / 'fetch-log.jsonl'
        out_dir = Path(options.out) if options.out else None
        db = PgImporter(options.dsn)
        try:
            reset(db)
            one, resu = [], []
            for index in range(options.repeats):
                run_id = 'one_shot_%d' % index
                log('one-shot run %d (2 SIGKILLs, restart from scratch)' % index)
                one.append(one_shot(db, run_id, fetch_log))
                run_id = 'resumable_%d' % index
                log('resumable run %d (2 SIGKILLs, resume from checkpoint)' % index)
                resu.append(resumable(db, run_id, fetch_log))
        finally:
            db.close()

        expected_hash = one[0]['dataset_hash']
        out['one_shot'] = one
        out['resumable'] = resu
        out['failures'] = collect_failures(one, resu, expected_hash)

        fetch_keys = ('fetches', 'distinct_pages', 'repeated_pages',
                      'bytes_fetched', 'bytes_distinct', 'repeated_bytes')
        out['comparison'] = compare(one, resu, fetch_keys)
        one_totals = out['comparison']['one_shot']['totals']
        resu_totals = out['comparison']['resumable']['totals']

        checks['one_shot_loses_nothing'] = (
            out['comparison']['one_shot']['missing_row_count'] == 0
            and out['comparison']['one_shot']['duplicate_row_count'] == 0
            and out['comparison']['one_shot']['duplicate_order_count'] == 0)
        checks['resumable_loses_nothing'] = (
            out['comparison']['resumable']['missing_row_count'] == 0
            and out['comparison']['resumable']['duplicate_row_count'] == 0
            and out['comparison']['resumable']['duplicate_order_count'] == 0)
        checks['one_shot_discards_partial_progress_on_restart'] = all(
            run['discarded_rows'] > 0 for run in one)
        checks['resumable_never_discards_partial_progress'] = all(
            run['discarded_rows'] == 0 for run in resu)
        checks['resumable_repeats_strictly_fewer_pages'] = (
            resu_totals['repeated_pages'] > 0
            and resu_totals['repeated_pages'] < one_totals['repeated_pages'])
        checks['resumable_repeats_strictly_fewer_bytes'] = (
            resu_totals['repeated_bytes'] > 0
            and resu_totals['repeated_bytes'] < one_totals['repeated_bytes'])
        checks['resumable_fetches_strictly_fewer_pages_overall'] = (
            resu_totals['fetches'] < one_totals['fetches'])
        checks['both_strategies_produce_the_same_dataset'] = all(
            run['dataset_hash'] == expected_hash for run in one + resu)
        checks['all_kills_really_happened'] = all(
            run['kill_returncodes'] == [-9, -9, 0] for run in one + resu)
        checks['no_failures_recorded'] = not out['failures']

        out['checks'] = checks
        out['checks_met'] = sum(1 for value in checks.values() if value)
        out['checks_total'] = len(checks)
        out['all_met'] = all(checks.values())

        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'fetch-log.jsonl').write_text(
                fetch_log.read_text() if fetch_log.exists() else '')
            (out_dir / 'failures.json').write_text(
                json.dumps(out['failures'], indent=2, sort_keys=True) + '\n')

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['all_met'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
