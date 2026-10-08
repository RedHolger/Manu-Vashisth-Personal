"""P17-01: every opportunity has evidence or an explicit HYPOTHESIS label."""
import unittest

import discovery


class DiscoveryTests(unittest.TestCase):
    def test_real_artifacts_verify(self):
        rec = discovery.register_artifact(
            'p16-charter', 'release-plan/charter.json')
        self.assertEqual(rec['kind'], 'artifact')
        self.assertEqual(len(rec['sha256']), 64)
        self.assertTrue(discovery.verify(rec))

    def test_missing_artifact_refused(self):
        with self.assertRaises(FileNotFoundError):
            discovery.register_artifact('nope', 'launch-lab/nope.json')

    def test_hypothesis_labeled_passes_without_evidence(self):
        ranked = discovery.prioritize_labeled(
            [{'id': 'h', 'reach': 1, 'impact': 1, 'confidence': 0.5,
              'effort': 1, 'evidence': [], 'hypothesis': True}], [])
        self.assertEqual(ranked[0]['basis'], 'HYPOTHESIS')

    def test_unlabeled_unevidenced_rejected(self):
        with self.assertRaises(ValueError):
            discovery.prioritize_labeled(
                [{'id': 'x', 'reach': 1, 'impact': 1, 'confidence': 0.5,
                  'effort': 1, 'evidence': []}], [])

    def test_ranking_prefers_strong_evidence(self):
        evidence = [discovery.register_artifact(eid, rel) for eid, rel in (
            ('p16-charter', 'release-plan/charter.json'),
            ('p16-verify', 'release-plan/verify.py'))]
        ranked = discovery.prioritize_labeled(discovery.opportunities(),
                                             evidence)
        self.assertEqual(ranked[0]['id'], 'readiness-check')
        self.assertEqual(ranked[0]['basis'], 'evidence')
        hyps = [r for r in ranked if r['basis'] == 'HYPOTHESIS']
        self.assertEqual({r['id'] for r in hyps},
                         {'pilot-analytics', 'landing-page'})

    def test_audience_needs_are_hypotheses(self):
        self.assertIn('HYPOTHESIS', discovery.AUDIENCE['status'])


if __name__ == '__main__':
    unittest.main()
