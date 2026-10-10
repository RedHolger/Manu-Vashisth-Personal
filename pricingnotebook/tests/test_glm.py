"""GLM tests: leakage, closed-form checks, known-truth recovery, calibration."""
import json
import sys
import unittest

import numpy as np

sys.path.insert(0, "src")
from glm import design, ols, poisson_irls  # noqa: E402


class TestLeakage(unittest.TestCase):
    def test_periods_disjoint_and_clean(self):
        rows = np.genfromtxt("datasets/policies.csv", delimiter=",", names=True)
        with open("datasets/truth.json") as fh:
            truth = json.load(fh)
        self.assertEqual(set(rows["period"]) & set(truth["test_periods"]),
                         set(truth["test_periods"]) - set(truth["train_periods"]))
        self.assertTrue(set(truth["train_periods"]).isdisjoint(truth["test_periods"]))
        self.assertTrue(np.all(rows["exposure"] > 0))
        self.assertFalse(np.any(np.isnan(rows["claims"])))


class TestClosedForms(unittest.TestCase):
    def test_intercept_only_poisson_is_log_mean(self):
        rng = np.random.default_rng(0)
        y = rng.poisson(2.0, size=500).astype(float)
        X = np.ones((500, 1))
        beta, _, _ = poisson_irls(X, y, np.zeros(500))
        self.assertAlmostEqual(beta[0], np.log(y.mean()), places=6)

    def test_ols_exact_on_noiseless(self):
        X = np.column_stack([np.ones(50), np.arange(50, dtype=float)])
        beta, _ = ols(X, 3.0 * X[:, 1] - 1.0)
        self.assertAlmostEqual(beta[0], -1.0, places=8)
        self.assertAlmostEqual(beta[1], 3.0, places=8)

    def test_intercept_only_varying_exposure(self):
        # Analytical MLE: log(sum(y) / sum(exposure)). Audit case: y=[1,2,3,4],
        # exposure=[.5,1,1.5,2] -> log(10/5) = log 2. Predicted total must be 10.
        y = np.array([1., 2., 3., 4.])
        exposure = np.array([.5, 1., 1.5, 2.])
        X = np.ones((4, 1))
        beta, _, info = poisson_irls(X, y, np.log(exposure))
        self.assertAlmostEqual(beta[0], np.log(2.0), places=6)
        self.assertLessEqual(info["n_iter"], 100)
        total = float(np.exp(X @ beta + np.log(exposure)).sum())
        self.assertAlmostEqual(total, 10.0, places=6)

    def test_slope_with_varying_exposure(self):
        # Two groups, known rates: group A rate 2.0 (exposure 1 x4), group B
        # rate 0.5 (exposure 2 x4). y = exact means -> intercept log 2, slope log(0.25).
        y = np.array([2., 2., 2., 2., 1., 1., 1., 1.])
        exposure = np.array([1., 1., 1., 1., 2., 2., 2., 2.])
        X = np.column_stack([np.ones(8), np.array([0.] * 4 + [1.] * 4)])
        beta, _, _ = poisson_irls(X, y, np.log(exposure))
        self.assertAlmostEqual(beta[0], np.log(2.0), places=6)
        self.assertAlmostEqual(beta[1], np.log(0.25), places=6)

    def test_invalid_inputs_rejected(self):
        X = np.ones((3, 1))
        with self.assertRaises(ValueError):
            poisson_irls(X, np.array([-1., 0., 1.]), np.zeros(3))
        with self.assertRaises(ValueError):
            poisson_irls(X, np.array([1., 0., 1.]), np.array([0., 0., -np.inf]))
        with self.assertRaises(ValueError):
            poisson_irls(np.ones((2, 1)), np.ones(3), np.zeros(3))

    def test_nonconvergence_raises(self):
        # Separated data with max_iter=1 cannot converge; must raise, not silently return.
        X = np.column_stack([np.ones(20), np.arange(20, dtype=float)])
        y = (np.arange(20) > 10).astype(float) * 50.0
        with self.assertRaises(RuntimeError):
            poisson_irls(X, y, np.zeros(20), max_iter=1)


class TestRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("results/fit.json") as fh:
            cls.fit = json.load(fh)
        with open("datasets/truth.json") as fh:
            cls.truth = json.load(fh)

    def test_frequency_recovers_truth(self):
        for c in ("young", "urban", "suv"):
            self.assertLess(abs(self.fit["freq_beta"][c] - self.truth["B_FREQ"][c]), 0.15)
        self.assertLess(abs(self.fit["freq_beta"]["intercept"] - self.truth["B_FREQ"]["intercept"]), 0.25)

    def test_irls_converged_and_recorded(self):
        self.assertIn("irls", self.fit)
        self.assertLessEqual(self.fit["irls"]["n_iter"], 100)

    def test_severity_recovers_truth(self):
        for c in ("intercept", "suv", "urban"):
            self.assertLess(abs(self.fit["sev_beta"][c] - self.truth["B_SEV"][c]), 0.1)
        self.assertLess(abs(self.fit["sev_beta"]["young"]), 0.15)  # null effect stays small

    def test_lift_positive(self):
        self.assertGreater(self.fit["test_deviance"]["lift"], 0)
        lo, _ = self.fit["test_deviance"]["lift_ci95"]
        self.assertGreater(lo, 0)

    def test_calibration_tracks(self):
        for d in self.fit["calibration_deciles"]:
            self.assertLess(abs(d["pred"] - d["actual"]), 0.15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
