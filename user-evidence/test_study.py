"""P15-02..04: consent-gated capture, contradiction-retaining analysis, retest."""
import unittest

import study
from study import (Analysis, ConsentError, PopulationClaimError, Retest,
                   SessionCapture)


def _consent():
    return {'granted': True, 'form': 'v1'}


class CaptureTests(unittest.TestCase):
    def test_human_record_needs_consent(self):
        cap = SessionCapture()
        with self.assertRaises(ConsentError):
            cap.record('t', True, 10, 'obs', consent=None,
                       synthetic=False, pii_checked=True)

    def test_human_record_needs_pii_check(self):
        cap = SessionCapture()
        with self.assertRaises(ConsentError):
            cap.record('t', True, 10, 'obs', consent=_consent(),
                       synthetic=False, pii_checked=False)

    def test_pii_in_observation_refused(self):
        cap = SessionCapture()
        with self.assertRaises(ConsentError):
            cap.record('t', True, 10, 'contact me@x.com', consent=_consent(),
                       synthetic=False, pii_checked=True)

    def test_synthetic_fixtures_tagged_and_excluded(self):
        cap = SessionCapture()
        cap.record('t', True, 10, 'fixture', synthetic=True)
        self.assertEqual(len(cap.human_sessions()), 0)
        self.assertEqual(len(cap.synthetic_sessions()), 1)

    def test_consenting_capture_assigns_pseudonyms(self):
        cap = SessionCapture()
        r1 = cap.record('t', True, 10, 'obs one', consent=_consent(),
                        synthetic=False, pii_checked=True)
        r2 = cap.record('t', False, 20, 'obs two', consent=_consent(),
                        synthetic=False, pii_checked=True)
        self.assertEqual((r1['participant'], r2['participant']),
                         ('P-001', 'P-002'))
        self.assertFalse(r1['synthetic'])


class AnalysisTests(unittest.TestCase):
    def _sessions(self):
        return [
            {'participant': 'P-001', 'task': 't', 'success': True,
             'seconds': 10, 'observation': 'found it', 'codes': ['visibility'],
             'synthetic': False},
            {'participant': 'P-002', 'task': 't', 'success': False,
             'seconds': 40, 'observation': 'missed it', 'codes': ['visibility'],
             'synthetic': False},
        ]

    def test_contradictions_retained_not_averaged(self):
        analysis = Analysis(self._sessions())
        contra = analysis.contradictions()
        self.assertIn('visibility', contra)
        self.assertTrue(contra['visibility']['success'])
        self.assertTrue(contra['visibility']['fail'])

    def test_participant_vs_observation_counts_separate(self):
        sessions = self._sessions() + [
            {'participant': 'P-001', 'task': 't2', 'success': True,
             'seconds': 5, 'observation': 'again', 'codes': [],
             'synthetic': False}]
        counts = Analysis(sessions).counts()
        self.assertEqual(counts['participants'], 2)
        self.assertEqual(counts['observations'], 3)

    def test_annotation_does_not_touch_observation(self):
        analysis = Analysis(self._sessions())
        analysis.annotate('P-001', 't', 'maybe the label is small')
        row = next(s for s in analysis.sessions
                   if s['participant'] == 'P-001')
        self.assertEqual(row['observation'], 'found it')
        self.assertEqual(analysis.notes[('P-001', 't')],
                         'maybe the label is small')

    def test_second_coder_sample_must_be_real(self):
        analysis = Analysis(self._sessions())
        with self.assertRaises(KeyError):
            analysis.mark_second_coder_review([('P-999', 't')], 'coder-2')
        marked = analysis.mark_second_coder_review([('P-001', 't')], 'coder-2')
        self.assertEqual(len(marked), 1)


class RetestTests(unittest.TestCase):
    def _rows(self, task, n, completed):
        return [{'participant': 's-%d' % i, 'task': task,
                 'success': i < completed, 'seconds': 10 + i,
                 'observation': 'fixture', 'codes': [], 'synthetic': True}
                for i in range(n)]

    def test_matched_comparison_with_disclaimer(self):
        retest = Retest(self._rows('t', 4, 2), self._rows('t', 4, 3))
        out = retest.compare()
        self.assertEqual(out['matched_tasks'], ['t'])
        self.assertEqual(out['delta']['t']['completed_before'], 2)
        self.assertEqual(out['delta']['t']['completed_after'], 3)
        self.assertIn('convenience sample', out['disclaimer'])

    def test_unmatched_comparison_refused(self):
        retest = Retest(self._rows('t1', 2, 1), self._rows('t2', 2, 1))
        with self.assertRaises(ValueError):
            retest.compare()

    def test_population_claim_refused(self):
        retest = Retest(self._rows('t', 2, 1), self._rows('t', 2, 1))
        for kind in ('population', 'generalize', 'causal'):
            with self.assertRaises(PopulationClaimError):
                retest.claim(kind)


if __name__ == '__main__':
    unittest.main()
