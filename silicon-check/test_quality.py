"""P21-03: seeded RTL defect caught by differential AND assertions."""
import unittest
from pathlib import Path

import differential
import quality


def _sim_trace():
    return [(1, 1, i % 256, 0) for i in range(30)] + [(0, 1, 0, 0)] * 6


def _write_trace(trace):
    import tempfile
    handle = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
    handle.write(''.join('%d %d %d %d\n' % t for t in trace))
    handle.close()
    return handle.name


class QualityTests(unittest.TestCase):
    def test_defect_is_a_real_rtl_change(self):
        good = Path('fifo.sv').read_text(encoding='utf-8')
        bad = Path('fifo_buggy.sv').read_text(encoding='utf-8')
        self.assertNotEqual(good, bad)
        self.assertIn('SEEDED DEFECT', bad)
        self.assertNotIn('SEEDED DEFECT', good)
        self.assertIn("2'b11:count<=count+1", bad.replace(' ', ''))

    def test_differential_catches_buggy(self):
        result = differential.run_seed(7, cycles=200, dut='fifo_buggy.sv',
                                       workdir='/tmp/p21q')
        self.assertGreater(result['n_mismatches'], 0)
        self.assertTrue(isinstance(result['trace'], list))
        self.assertEqual(len(result['trace']), 200)

    def test_assertions_pass_on_good_fail_on_buggy(self):
        path = _write_trace(_sim_trace())
        try:
            good = quality.run_assertions(path, dut='fifo.sv',
                                          workdir='/tmp/p21q-good')
            bad = quality.run_assertions(path, dut='fifo_buggy.sv',
                                         workdir='/tmp/p21q-bug')
        finally:
            Path(path).unlink()
        self.assertTrue(good['pass'])
        self.assertFalse(bad['pass'])
        self.assertIn('A6', bad['simulate']['log'])

    def test_coverage_report_honest(self):
        report = quality.coverage_report()
        self.assertTrue(report['covered_properties'])
        self.assertTrue(report['untested'])
        self.assertIn('not silicon', report['signoff_disclaimer'])
        self.assertTrue(any('DEPTH' in u for u in report['untested']))


if __name__ == '__main__':
    unittest.main()
