"""P06-03 fault matrix wired into the unittest suite."""
import contextlib
import io
import json
import unittest

try:
    import psycopg
    import fault_matrix
    from pg_adapter import DEFAULT_DSN
except Exception as _exc:  # pragma: no cover - exercised only without psycopg
    psycopg = None
    DEFAULT_DSN = str(_exc)
    fault_matrix = None


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
SKIP_REASON = ('requires psycopg and a running P06 PostgreSQL (%s)'
               % DEFAULT_DSN)


@unittest.skipUnless(AVAILABLE, SKIP_REASON)
class FaultMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cls.exit_code = fault_matrix.main([])
        cls.result = json.loads(buffer.getvalue())

    def test_harness_exits_zero_with_every_check_met(self):
        self.assertEqual(self.exit_code, 0, self.result['checks'])
        self.assertEqual(self.result['checks_met'], self.result['checks_total'])
        self.assertTrue(self.result['all_met'])

    def test_resumed_snapshot_equals_a_clean_run(self):
        self.assertEqual(self.result['clean_run']['dataset_hash'],
                         self.result['faulted_run']['dataset_hash'])
        self.assertTrue(self.result['datasets_identical'])
        self.assertEqual(self.result['clean_run']['state'],
                         self.result['faulted_run']['state'])

    def test_workers_really_were_terminated(self):
        codes = [item['worker']['returncode']
                 for item in self.result['process_kills']]
        self.assertEqual(codes[:2], [-9, -9])
        self.assertEqual(codes[2], 0)
        for item in self.result['process_kills'][:2]:
            self.assertTrue(item['worker']['killed_by_sigkill'], item)

    def test_kill_inside_transaction_rolled_back_the_whole_page(self):
        observed = self.result['process_kills'][0]['observed']
        self.assertEqual(observed['rows'], observed['seen'])
        self.assertEqual(observed['rows'], self.result['page_size'])
        self.assertEqual(observed['done'], 0)

    def test_matrix_covers_every_fault_class(self):
        outcomes = [entry['outcome'] for entry in self.result['fault_matrix']]
        self.assertEqual(outcomes.count('explicit IntegrityError'), 5)
        self.assertEqual(outcomes.count('quarantined'), 3)
        self.assertFalse(any(entry['silent_truncated_success']
                             for entry in self.result['fault_matrix']))

    def test_checkpoint_never_runs_ahead_of_written_rows(self):
        self.assertTrue(
            self.result['checks']['checkpoint_never_runs_ahead_of_the_rows_written'])


if __name__ == '__main__':
    unittest.main()
