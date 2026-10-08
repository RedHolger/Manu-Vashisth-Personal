"""P09-01: entity splits never leak; license and hashes recorded."""
import json
import unittest

from dataset import DATA_DIR, generate, load_dataset, save_dataset
from project import validate_splits
from splits import entity_split, write_split_manifest


class SplitTests(unittest.TestCase):
    def test_no_entity_overlap(self):
        _, _, entities, samples = generate()
        parts = entity_split(samples, entities, seed=0)
        trains = {samples[i] for i in []}
        # Rebuild entity sets per partition from the id prefix.
        by_part = {}
        entity_of = dict(zip(samples, entities))
        for name, ids in parts.items():
            by_part[name] = {entity_of[sample] for sample in ids}
        self.assertFalse(by_part['train'] & by_part['validation'])
        self.assertFalse(by_part['train'] & by_part['test'])
        self.assertFalse(by_part['validation'] & by_part['test'])
        # Sample ids are disjoint too.
        self.assertEqual(len(sum(parts.values(), [])),
                         len(set(sum(parts.values(), []))))
        # Reference kernel agrees there is no leakage.
        rows = {name: [{'id': sample, 'group': entity_of[sample]}
                       for sample in ids]
                for name, ids in parts.items()}
        validate_splits(rows['train'], rows['validation'], rows['test'])

    def test_deterministic_and_hashed(self):
        _, _, entities, samples = generate()
        first = entity_split(samples, entities, seed=0)
        second = entity_split(samples, entities, seed=0)
        self.assertEqual(first, second)
        manifest = write_split_manifest(samples, entities, 0,
                                        DATA_DIR / 'splits.check.json')
        try:
            for name in ('train', 'validation', 'test'):
                self.assertEqual(len(manifest['partitions'][name]
                                     ['sample_sha256']), 64)
            total = sum(manifest['partitions'][name]['n_samples']
                        for name in ('train', 'validation', 'test'))
            self.assertEqual(total, 300)
            # 60/20/20 of 30 entities.
            self.assertEqual(manifest['partitions']['train']['n_entities'],
                             18)
            self.assertEqual(
                manifest['partitions']['validation']['n_entities'], 6)
            self.assertEqual(manifest['partitions']['test']['n_entities'], 6)
        finally:
            (DATA_DIR / 'splits.check.json').unlink(missing_ok=True)

    def test_leakage_fixture_rejected(self):
        with self.assertRaises(ValueError):
            validate_splits([{'id': 'a', 'group': 'p'}], [],
                            [{'id': 'b', 'group': 'p'}])

    def test_dataset_manifest_records_license(self):
        manifest = save_dataset()
        on_disk = json.loads((DATA_DIR / 'manifest.json').read_text())
        self.assertEqual(on_disk['license'], 'CC0-1.0')
        self.assertEqual(on_disk['n_images'], 300)
        self.assertEqual(len(on_disk['sha256']), 64)
        pack = load_dataset()
        self.assertEqual(pack['images'].shape, (300, 8, 8))
        self.assertEqual(len(pack['sample_ids']), 300)


if __name__ == '__main__':
    unittest.main()
