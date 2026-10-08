"""Unit tests for the P06-04 evaluation: fetch accounting and failure archiving."""
import json
import tempfile
import unittest
from pathlib import Path

try:
    from evaluate_import import collect_failures, fetch_metrics, summarise
except Exception as _exc:  # pragma: no cover - exercised only without psycopg
    collect_failures = fetch_metrics = summarise = None
    _IMPORT_ERROR = str(_exc)
else:
    _IMPORT_ERROR = ''

SKIP_REASON = 'evaluate_import needs psycopg: %s' % _IMPORT_ERROR


def make_fetch_log(entries, run='one_shot_0'):
    handle = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
    handle.close()
    path = Path(handle.name)
    with open(path, 'w', encoding='utf-8') as stream:
        for index, (cursor, size) in enumerate(entries):
            stream.write(json.dumps({
                'run': run, 'source': 'src', 'cursor': cursor,
                'next': None, 'start': cursor, 'rows': 3, 'bytes': size,
                'fetch_ms': 1.0, 'pid': 1, 'at': float(index),
            }) + '\n')
    return path


def workers(*codes):
    return [{'returncode': code, 'stderr': ''} for code in codes]


def make_run(**overrides):
    run = {
        'run': 'one_shot_0',
        'strategy': 'one-shot',
        'missing_row_count': 0,
        'missing_rows': [],
        'duplicate_row_count': 0,
        'duplicate_order_count': 0,
        'fetches': {'repeated_pages': 3, 'repeated_bytes': 660},
        'state': {'rows': 12, 'done': 1, 'orders': 10, 'quarantined': 2},
        'dataset_hash': 'aaa',
        'workers': workers(-9, -9, 0),
        'kill_returncodes': [-9, -9, 0],
        'discarded_rows': 6,
    }
    run.update(overrides)
    return run


def resumable_run(**overrides):
    overrides.setdefault('run', 'resumable_0')
    overrides.setdefault('strategy', 'resumable')
    overrides.setdefault('discarded_rows', 0)
    overrides.setdefault('fetches', {'repeated_pages': 1, 'repeated_bytes': 266})
    return make_run(**overrides)


@unittest.skipIf(fetch_metrics is None, SKIP_REASON)
class FetchMetricsTest(unittest.TestCase):
    def test_each_page_fetched_once_reports_no_repeats(self):
        log = make_fetch_log([('0', 100), ('3', 110), ('6', 120), ('9', 130)])
        metrics = fetch_metrics(log, 'one_shot_0')
        self.assertEqual(metrics['fetches'], 4)
        self.assertEqual(metrics['distinct_pages'], 4)
        self.assertEqual(metrics['repeated_pages'], 0)
        self.assertEqual(metrics['repeated_bytes'], 0)
        self.assertEqual(metrics['bytes_fetched'], 460)

    def test_a_refetched_page_counts_as_a_repeated_page_and_bytes(self):
        log = make_fetch_log([('0', 100), ('3', 110), ('3', 110), ('6', 120)],
                             run='resumable_0')
        metrics = fetch_metrics(log, 'resumable_0')
        self.assertEqual(metrics['fetches'], 4)
        self.assertEqual(metrics['distinct_pages'], 3)
        self.assertEqual(metrics['repeated_pages'], 1)
        self.assertEqual(metrics['repeated_bytes'], 110)
        self.assertEqual(metrics['cursor_sequence'], ['0', '3', '3', '6'])

    def test_other_runs_are_ignored(self):
        log = make_fetch_log([('0', 100)], run='resumable_0')
        self.assertEqual(fetch_metrics(log, 'one_shot_0')['fetches'], 0)
        self.assertEqual(fetch_metrics(log, 'resumable_0')['fetches'], 1)


@unittest.skipIf(collect_failures is None, SKIP_REASON)
class SummaryTest(unittest.TestCase):
    def test_min_median_max(self):
        summary = summarise([{'ms': 10}, {'ms': 30}, {'ms': 20}], 'ms')
        self.assertEqual(summary, {'min': 10, 'median': 20, 'max': 30,
                                   'samples': 3})

    def test_none_values_are_skipped(self):
        summary = summarise([{'ms': None}, {'ms': 4}], 'ms')
        self.assertEqual(summary['min'], 4)
        self.assertEqual(summary['samples'], 1)


@unittest.skipIf(collect_failures is None, SKIP_REASON)
class FailureArchiveTest(unittest.TestCase):
    def test_clean_runs_archive_no_failures(self):
        self.assertEqual(collect_failures([make_run()], [resumable_run()],
                                          'aaa'), [])

    def test_missing_rows_are_archived(self):
        failures = collect_failures(
            [make_run(missing_row_count=2, missing_rows=[3, 7])], [], 'aaa')
        self.assertEqual(len(failures), 1)
        self.assertIn('missing rows: [3, 7]', failures[0]['detail'])

    def test_duplicate_orders_are_archived(self):
        failures = collect_failures(
            [], [resumable_run(duplicate_order_count=1)], 'aaa')
        self.assertTrue(any('duplicate rows/orders' in f['detail']
                            for f in failures))

    def test_divergent_dataset_hash_is_a_failure(self):
        failures = collect_failures([make_run(dataset_hash='bbb')], [], 'aaa')
        self.assertTrue(any('differs from the reference' in f['detail']
                            for f in failures))

    def test_an_unexpected_kill_return_code_is_a_failure(self):
        failures = collect_failures(
            [], [resumable_run(kill_returncodes=[0, -9, 0],
                               workers=workers(0, -9, 0))], 'aaa')
        self.assertTrue(any('exit codes' in f['detail'] for f in failures))

    def test_a_worker_writing_to_stderr_is_a_failure(self):
        noisy = workers(-9, -9, 0)
        noisy[2]['stderr'] = 'boom'
        failures = collect_failures([], [resumable_run(workers=noisy)], 'aaa')
        self.assertTrue(any('stderr' in f['detail'] for f in failures))

    def test_an_incomplete_run_is_a_failure(self):
        incomplete = {'rows': 6, 'done': 0, 'orders': 0, 'quarantined': 0}
        failures = collect_failures([], [resumable_run(state=incomplete)],
                                    'aaa')
        self.assertTrue(any('did not complete' in f['detail'] for f in failures))

    def test_a_one_shot_run_that_never_discards_progress_is_a_failure(self):
        failures = collect_failures([make_run(discarded_rows=0)], [], 'aaa')
        self.assertTrue(any('never discarded partial progress' in f['detail']
                            for f in failures))

    def test_a_resumable_run_that_discards_progress_is_a_failure(self):
        failures = collect_failures([], [resumable_run(discarded_rows=3)], 'aaa')
        self.assertEqual(len(failures), 1)
        self.assertIn('must keep its checkpoint', failures[0]['detail'])


if __name__ == '__main__':
    unittest.main()
