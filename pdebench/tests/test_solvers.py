"""Milestone 1+2 tests: hand-calculated fixtures, convergence, negative paths."""
import math
import sys
import unittest

sys.path.insert(0, "src")
from heat1d import initial_sine, l2_error, solve as heat_solve, step
from poisson2d import jacobi_sweep, manufactured, residual
from poisson2d import solve as poisson_solve


class TestHeatFixtures(unittest.TestCase):
    def test_one_step_matches_hand_calc(self):
        u0, dx = initial_sine(5)  # dx = 0.25
        self.assertAlmostEqual(dx, 0.25, places=12)
        u1 = step(u0, 0.25)
        for got, want in zip(u1, [0.0, 0.60355339, 0.85355339, 0.60355339, 0.0]):
            self.assertAlmostEqual(float(got), want, places=8)

    def test_boundaries_pinned(self):
        u0, _ = initial_sine(9)
        u = u0
        for _ in range(10):
            u = step(u, 0.4)
        self.assertEqual(u[0], 0.0)
        self.assertEqual(u[-1], 0.0)

    def test_spatial_convergence_order_two(self):
        x1, u1 = heat_solve(21, 1.0, 0.001, 0.02)
        x2, u2 = heat_solve(41, 1.0, 0.00025, 0.02)
        e_coarse = l2_error(u1, x1, 0.02)
        e_fine = l2_error(u2, x2, 0.02)
        ratio = e_coarse / e_fine
        self.assertGreater(ratio, 3.0, f"expected ~4x error drop, got {ratio:.2f}")
        self.assertLess(e_fine, 1e-4)

    def test_cfl_violation_raises(self):
        with self.assertRaises(ValueError):
            heat_solve(11, 1.0, 0.01, 0.02)  # r = 1.0 > 0.5

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            heat_solve(2, 1.0, 0.001, 0.02)
        with self.assertRaises(ValueError):
            heat_solve(11, 1.0, -0.001, 0.02)


class TestPoissonFixtures(unittest.TestCase):
    def test_one_sweep_matches_hand_calc(self):
        import numpy as np
        f, _, h = manufactured(3)  # single interior point, h = 0.5
        self.assertAlmostEqual(h, 0.5, places=12)
        self.assertAlmostEqual(float(f[1, 1]), 2.0 * math.pi**2, places=6)
        u = jacobi_sweep(np.zeros((3, 3)), f, h)
        self.assertAlmostEqual(float(u[1, 1]), 1.233700550, places=6)

    def test_residual_decreases_and_converges(self):
        out = poisson_solve(17, tol=1e-4, max_iter=20000)
        self.assertLess(out["residual"], 1e-4)
        self.assertLess(out["residual"], out["residual0"])
        self.assertTrue(out["monotone"])

    def test_refinement_reduces_error(self):
        a = poisson_solve(9, tol=1e-6, max_iter=20000)
        b = poisson_solve(17, tol=1e-6, max_iter=20000)
        self.assertLess(b["linf"], a["linf"])

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            manufactured(2)
        with self.assertRaises(ValueError):
            poisson_solve(9, tol=-1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
