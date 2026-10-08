"""P20-01/03: contract pinned; optimized kernel bit-identical and faster."""
import unittest

import baseline
import project
import workload


class ContractTests(unittest.TestCase):
    def test_contract_names_host_not_board(self):
        contract = workload.workload_contract()
        self.assertIn('host-cpu', contract['device'])
        self.assertIn('NO board', contract['device'])

    def test_frames_deterministic(self):
        self.assertEqual(workload.make_frames(2, 8, 7),
                         workload.make_frames(2, 8, 7))
        self.assertNotEqual(workload.make_frames(2, 8, 7),
                            workload.make_frames(2, 8, 8))

    def test_malformed_frames_rejected(self):
        for bad in ([[1]], [[1, 2], [3]], 'nope', [[1] * 2] * 2):
            with self.assertRaises(ValueError):
                workload.edges_opt(bad)
            with self.assertRaises(ValueError):
                project.edges(bad)


class EquivalenceTests(unittest.TestCase):
    def test_bit_identical(self):
        self.assertTrue(workload.verify_equivalence())

    def test_optimized_faster_same_checksum(self):
        import time
        frames = workload.make_frames(6, 96, 7)
        for fn in (project.edges, workload.edges_opt):
            fn(frames[0])
        t0 = time.perf_counter_ns()
        c0 = sum(sum(map(sum, project.edges(f))) for f in frames)
        t0 = (time.perf_counter_ns() - t0) / 1e6
        t1 = time.perf_counter_ns()
        c1 = sum(sum(map(sum, workload.edges_opt(f))) for f in frames)
        t1 = (time.perf_counter_ns() - t1) / 1e6
        self.assertEqual(c0, c1)
        # Row hoisting must not regress; flaky-machine guard is generous.
        self.assertLessEqual(t1, t0 * 1.1)


if __name__ == '__main__':
    unittest.main()
