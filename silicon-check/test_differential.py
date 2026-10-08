"""P21-02: seeded differential RTL-vs-model agreement + directed boundaries."""
import unittest

import differential
from differential import compare, directed_traces, gen_trace, run_seed


class DifferentialTests(unittest.TestCase):
    def test_trace_deterministic(self):
        self.assertEqual(gen_trace(7, 50), gen_trace(7, 50))
        self.assertNotEqual(gen_trace(7, 50), gen_trace(8, 50))

    def test_seed_matches_model(self):
        result = run_seed(11, cycles=60, workdir='/tmp/p21test')
        self.assertEqual(result['compile_exit'], 0)
        self.assertEqual(result['simulate_exit'], 0)
        self.assertEqual(result['n_mismatches'], 0, result['mismatches'][:2])

    def test_directed_boundaries_match(self):
        for name, trace in directed_traces().items():
            out = differential.run_directed(name, trace,
                                            workdir='/tmp/p21test')
            self.assertEqual(out['n_mismatches'], 0,
                             (name, out['mismatches'][:2]))

    def test_comparator_bites_on_doctored_result(self):
        trace = gen_trace(5, 20)
        result = run_seed(5, cycles=20, workdir='/tmp/p21test')
        self.assertEqual(result['n_mismatches'], 0)
        doctored = [dict(r) for r in result['results']]
        doctored[3]['wa'] = 1 - doctored[3]['wa']
        mismatches = compare(trace, doctored)
        self.assertTrue(any(m['cycle'] == 3 and m['field'] == 'wa'
                            for m in mismatches))

    def test_cycle_count_mismatch_flagged(self):
        trace = gen_trace(5, 20)
        result = run_seed(5, cycles=20, workdir='/tmp/p21test')
        short = result['results'][:10]
        mismatches = compare(trace, short)
        self.assertTrue(any(m['field'] == 'cycle_count' for m in mismatches))


if __name__ == '__main__':
    unittest.main()
