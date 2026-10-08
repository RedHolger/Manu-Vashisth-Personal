"""P10-02: versioned annotation store, budget accounting, review queue."""
import unittest

from annotation import AnnotationStore, Budget, BudgetExceeded


class _Clock:
    """Deterministic monotonic clock so evidence is reproducible."""

    def __init__(self, start=1000.0, step=1.0):
        self.t = start
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


class AnnotationStoreTests(unittest.TestCase):
    def setUp(self):
        self.clock = _Clock()
        self.store = AnnotationStore(budget=Budget(10), clock=self.clock)

    def test_every_change_has_author_time_version(self):
        record, changed = self.store.label('a', 1, 'alice')
        self.assertTrue(changed)
        self.assertEqual(record['author'], 'alice')
        self.assertEqual(record['version'], 1)
        self.assertIsInstance(record['at'], float)
        self.assertGreater(record['at'], 0)

    def test_author_is_required(self):
        with self.assertRaises(ValueError):
            self.store.label('a', 1, '')

    def test_repeated_identical_label_is_idempotent(self):
        first, c1 = self.store.label('a', 1, 'alice')
        second, c2 = self.store.label('a', 1, 'alice')
        self.assertTrue(c1)
        self.assertFalse(c2)                 # no new version
        self.assertEqual(first, second)      # same record returned
        self.assertEqual(self.store.acquired_count, 1)
        self.assertEqual(self.store.budget.spent, 1)   # charged once

    def test_repeated_labels_do_not_inflate_acquired_count(self):
        for _ in range(5):
            self.store.label('a', 1, 'alice')
        for _ in range(3):
            self.store.label('b', 0, 'bob')
        self.assertEqual(self.store.acquired_count, 2)
        self.assertEqual(sorted(self.store.acquired_ids()), ['a', 'b'])
        self.assertEqual(self.store.budget.spent, 2)

    def test_correction_appends_version_without_recharging(self):
        self.store.label('a', 1, 'alice')
        record, changed = self.store.label('a', 0, 'carol')   # correction
        self.assertTrue(changed)
        self.assertEqual(record['version'], 2)
        self.assertEqual(record['prior_value'], 1)
        self.assertEqual(record['author'], 'carol')
        self.assertEqual(self.store.acquired_count, 1)       # still one id
        self.assertEqual(self.store.budget.spent, 1)         # not recharged
        self.assertEqual(self.store.value('a'), 0)
        self.assertEqual(len(self.store.history('a')), 2)

    def test_budget_enforced_on_new_ids(self):
        small = AnnotationStore(budget=Budget(2), clock=self.clock)
        small.label('a', 1, 'alice')
        small.label('b', 1, 'bob')
        with self.assertRaises(BudgetExceeded):
            small.label('c', 1, 'carol')     # third distinct id exceeds 2

    def test_history_is_append_only_audit_trail(self):
        self.store.label('a', 1, 'alice')
        self.store.label('a', 0, 'carol')
        self.store.label('b', 1, 'bob')
        trail = self.store.audit_trail()
        self.assertEqual(len(trail), 3)
        self.assertEqual([r['version'] for r in trail if r['id'] == 'a'],
                         [1, 2])
        authors = [r['author'] for r in trail]
        self.assertEqual(authors, ['alice', 'carol', 'bob'])

    def test_current_and_labeled_items(self):
        self.store.label('a', 1, 'alice')
        self.store.label('a', 0, 'carol')
        self.assertEqual(self.store.current('a')['value'], 0)
        self.assertEqual(self.store.labeled_items(), {'a': 0})
        self.assertIsNone(self.store.current('missing'))


class ReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.clock = _Clock()
        self.store = AnnotationStore(budget=Budget(10), clock=self.clock)

    def test_enqueue_and_no_duplicate_pending(self):
        self.assertTrue(self.store.review.enqueue('a', 'low confidence'))
        self.assertFalse(self.store.review.enqueue('a', 'again'))
        self.assertEqual(self.store.review.pending(), ['a'])

    def test_label_can_flag_for_review(self):
        self.store.label('a', 1, 'alice', review=True, reason='uncertain')
        self.assertEqual(self.store.review.pending(), ['a'])
        self.assertEqual(self.store.review.reason('a')['reason'], 'uncertain')

    def test_resolve_records_reviewer_and_verdict(self):
        self.store.review.enqueue('a', 'uncertain')
        record = self.store.review.resolve('a', 'carol', 'corrected')
        self.assertEqual(record['reviewer'], 'carol')
        self.assertEqual(record['verdict'], 'corrected')
        self.assertEqual(self.store.review.pending(), [])
        self.assertEqual(len(self.store.review.resolved), 1)

    def test_resolve_unknown_or_bad_verdict(self):
        with self.assertRaises(KeyError):
            self.store.review.resolve('nope', 'carol', 'approved')
        self.store.review.enqueue('a', 'x')
        with self.assertRaises(ValueError):
            self.store.review.resolve('a', 'carol', 'maybe')


class BudgetTests(unittest.TestCase):
    def test_charge_and_remaining(self):
        budget = Budget(3)
        self.assertEqual(budget.remaining, 3)
        budget.charge(2)
        self.assertEqual(budget.spent, 2)
        self.assertEqual(budget.remaining, 1)
        with self.assertRaises(BudgetExceeded):
            budget.charge(2)

    def test_negative_charge_rejected(self):
        with self.assertRaises(ValueError):
            Budget(3).charge(-1)

    def test_as_dict(self):
        budget = Budget(5)
        budget.charge(1)
        self.assertEqual(budget.as_dict(),
                         {'total': 5, 'spent': 1, 'remaining': 4})


class OracleIntegrationTests(unittest.TestCase):
    def test_reveal_then_label_charges_once_per_id(self):
        """Acquire through the P10-01 oracle, then annotate the store."""
        from pool import build
        bundle = build(seed=7)
        oracle = bundle['oracle']
        store = AnnotationStore(budget=Budget(5), clock=_Clock())
        items = bundle['pool'].items()
        ids = [items[0]['id'], items[1]['id']]
        revealed = oracle.reveal(ids)
        for item_id in ids:
            store.label(item_id, revealed[item_id], 'annotator-1')
            store.label(item_id, revealed[item_id], 'annotator-1')  # repeat
        self.assertEqual(store.acquired_count, 2)
        self.assertEqual(store.budget.spent, 2)
        self.assertEqual(len(oracle.queried()), 2)


if __name__ == '__main__':
    unittest.main()
