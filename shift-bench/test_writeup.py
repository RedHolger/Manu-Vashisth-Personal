"""P09-04: write-up numbers match code; claims stay nonclinical."""
import unittest
from pathlib import Path

from corrupt import SEEDS
from intervention import average_over_seeds, run_intervention


def _avg(condition):
    values = [run_intervention(seed)['conditions'][condition]['accuracy']
              for seed in SEEDS]
    return sum(values) / len(values)


class WriteupTests(unittest.TestCase):
    def test_numbers_match_recomputation(self):
        self.assertAlmostEqual(_avg('baseline+raw'), 1.0)
        self.assertAlmostEqual(_avg('augmented+raw'), 1.0)
        # Augmented heavy noise is worse, not better (negative result).
        self.assertLess(_avg('augmented+raw+gaussian-noise-s2'),
                        _avg('baseline+raw+gaussian-noise-s2'))
        run = run_intervention(0)
        self.assertIn('baseline+raw+roll-s1', run['conditions'])
        self.assertAlmostEqual(
            run['conditions']['baseline+raw+roll-s1']['accuracy'], 0.5)
        # Write-up table matches recomputation to 3 decimals.
        memo = Path(__file__).with_name('WRITEUP.md').read_text()
        self.assertIn('%.3f' % _avg('baseline+raw+gaussian-noise-s2'), memo)
        self.assertIn('%.3f' % _avg('augmented+raw+gaussian-noise-s2'), memo)

    def test_negative_result_recorded(self):
        memo = Path(__file__).with_name('WRITEUP.md').read_text()
        self.assertIn('negative result', memo.lower())
        self.assertIn('does not help', memo.lower())

    def test_original_vs_known_separated(self):
        memo = Path(__file__).with_name('WRITEUP.md').read_text()
        lowered = memo.lower()
        self.assertIn('original contribution', lowered)
        self.assertIn('known methods', lowered)
        self.assertIn('temperature', lowered)

    def test_no_clinical_claim(self):
        memo = Path(__file__).with_name('WRITEUP.md').read_text()
        lowered = memo.lower()
        self.assertIn('no clinical utility', lowered)
        for phrase in ['deploy in clinic', 'improves diagnosis',
                       'patient outcomes', 'clinical validation']:
            self.assertNotIn(phrase, lowered)


if __name__ == '__main__':
    unittest.main()
