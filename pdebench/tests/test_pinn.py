"""PINN tests: smoke training (loss falls), saved-result acceptance."""
import json
import sys
import unittest

sys.path.insert(0, "src")
from pinn import evaluate, train


class TestPINN(unittest.TestCase):
    def test_smoke_training_falls(self):
        _, info = train(epochs=60, seed=0)
        self.assertLess(info["last_loss"], info["first_loss"])

    def test_saved_comparison(self):
        r = json.load(open("results/pinn.json"))
        self.assertLess(r["last_loss"], 1e-3)
        self.assertLess(r["l2_at_t002"], 1e-2)  # sane, not FD-beating
        self.assertEqual((r["seed"], r["epochs"], r["device"]), (11, 3000, "cpu"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
