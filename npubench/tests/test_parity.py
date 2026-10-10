"""Parity-bench tests: thresholds, agreement, recorded hashes, NPU honesty."""
import hashlib
import json
import unittest

import numpy as np
import onnxruntime as ort


class TestParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.load(open("package/meta.json"))
        cls.report = json.load(open("results/bench.json"))

    def test_model_hash_matches(self):
        with open("package/model.onnx", "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(h, self.meta["model_sha256"])
        self.assertEqual(h, self.report["model_sha256"])

    def test_weights_hash_matches_provenance(self):
        self.assertEqual(self.meta["weights_sha256"],
                         "1d1c0e9309c5d9df99851e8fc79d5b22f0e312aa00afb320b00f5779eb93b372")

    def test_parity_thresholds(self):
        r = self.report
        self.assertTrue(r["max_abs_diff"] < 1e-4 or r["max_rel_diff"] < 1e-5,
                        f"abs={r['max_abs_diff']} rel={r['max_rel_diff']}")
        self.assertEqual(r["top1_agreement"], "9/9")

    def test_cpu_provider_only(self):
        self.assertEqual(self.report["providers"], ["CPUExecutionProvider"])
        sess = ort.InferenceSession("package/model.onnx",
                                    providers=["CPUExecutionProvider"])
        x = np.load("package/inputs.npz")["sine_mel"].astype(np.float32)
        y = sess.run(["logits"], {"mel": x})[0]
        self.assertEqual(y.shape, (1, 10))

    def test_latency_reported(self):
        lat = self.report["latency_ms"]
        self.assertTrue(0 < lat["p50_ms"] <= lat["p90_ms"] <= lat["p99_ms"] < 1000)

    def test_npu_marked_skipped(self):
        self.assertIn("SKIPPED", self.report["npu_execution"])
        self.assertIn("not NPU results", self.report["npu_execution"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
