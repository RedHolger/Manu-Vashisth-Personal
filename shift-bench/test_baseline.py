"""P09-02: baseline reproducible from manifest + checkpoint."""
import json
import unittest

import numpy as np

from baseline import (fit_centroids, load_checkpoint, predict_logits,
                      save_checkpoint, train_and_evaluate)
from project import metrics


class BaselineTests(unittest.TestCase):
    def test_accuracy_above_chance_on_clean_patterns(self):
        report = train_and_evaluate()
        self.assertGreater(report['metrics']['test']['accuracy'], 0.9)
        self.assertGreater(report['metrics']['validation']['accuracy'], 0.9)

    def test_temperature_changes_nll_not_accuracy(self):
        report = train_and_evaluate()
        rows = [{'id': sample, 'logits': logit, 'label': label}
                for sample, logit, label in
                zip(report['ids']['test'], report['logits']['test'],
                    report['labels']['test'])]
        before = metrics(rows, temperature=1.0)
        after = metrics(rows, temperature=2.0)
        self.assertEqual(before['accuracy'], after['accuracy'])
        self.assertNotEqual(before['nll'], after['nll'])

    def test_checkpoint_reloads_identical_logits(self):
        report = train_and_evaluate()
        _, manifest = save_checkpoint(report['checkpoint'])
        try:
            centroids, reloaded = load_checkpoint()
            self.assertEqual(manifest, reloaded)
            from dataset import load_dataset
            pack = load_dataset()
            logits = predict_logits(pack['images'][:5], centroids)
            first = report['logits']
            # First five samples are train rows; recompute and compare.
            index = {sample: position
                     for position, sample in enumerate(pack['sample_ids'])}
            train_ids = report['ids']['train'][:5]
            expected = [first['train'][report['ids']['train'].index(sample)]
                        for sample in train_ids]
            for got, want in zip(logits, expected):
                self.assertAlmostEqual(got[0], want[0], places=9)
                self.assertAlmostEqual(got[1], want[1], places=9)
        finally:
            pass  # checkpoints/ is the tracked checkpoint, keep it.

    def test_manifest_pins_versions_and_data(self):
        report = train_and_evaluate()
        _, manifest = save_checkpoint(report['checkpoint'])
        self.assertIn('numpy', manifest['versions'])
        self.assertIn('python', manifest['versions'])
        self.assertEqual(manifest['dataset_sha256'],
                         report['dataset_manifest']['sha256'])
        self.assertEqual(len(manifest['centroid_sha256']), 64)

    def test_degenerate_fit_rejected(self):
        with self.assertRaises(ValueError):
            fit_centroids(np.zeros((4, 8, 8), dtype=np.float32), [0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
