"""P10-01: pool ids and hidden labels are separate interfaces."""
import unittest

from pool import Oracle, PoolView, build
from project import select


class PoolTests(unittest.TestCase):
    def test_entity_split_disjoint_and_hashed(self):
        bundle = build(seed=7)
        self.assertEqual(bundle['n_pool'], 100)
        self.assertEqual(bundle['n_test'], 50)
        self.assertFalse(set(bundle['pool_entities'])
                         & set(bundle['test_entities']))
        self.assertEqual(len(bundle['pool_sha256']), 64)
        self.assertEqual(len(bundle['test_sha256']), 64)
        repeat = build(seed=7)
        self.assertEqual(repeat['pool_sha256'], bundle['pool_sha256'])

    def test_pool_items_carry_no_labels(self):
        bundle = build()
        for item in bundle['pool'].items():
            self.assertEqual(set(item), {'id', 'x'})
            self.assertNotIn('y', item)

    def test_oracle_reveals_only_on_query(self):
        bundle = build()
        oracle = bundle['oracle']
        self.assertEqual(oracle.queried(), [])
        first = bundle['pool'].items()[0]['id']
        revealed = oracle.reveal([first])
        self.assertEqual(set(revealed), {first})
        self.assertEqual(oracle.queried(), [first])
        with self.assertRaises(ValueError):
            oracle.reveal(['no-such-id'])

    def test_selection_runs_on_label_free_pool(self):
        import random
        bundle = build()
        pool = bundle['pool'].items()
        for method in ('random', 'uncertainty', 'diversity'):
            index = select(pool, [], method, random.Random(1))
            self.assertTrue(0 <= index < len(pool))

    def test_unqueried_labels_stay_hidden(self):
        bundle = build()
        oracle = bundle['oracle']
        oracle.reveal([bundle['pool'].items()[0]['id']])
        self.assertEqual(len(oracle.queried()), 1)
        # 149 of 150 labels never revealed.
        self.assertEqual(len(oracle._labels) - len(oracle.queried()), 149)

    def test_test_ids_never_in_pool(self):
        bundle = build()
        pool_ids = {item['id'] for item in bundle['pool'].items()}
        self.assertFalse(pool_ids & set(bundle['test_ids']))


if __name__ == '__main__':
    unittest.main()
