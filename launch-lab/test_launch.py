"""P17-03/04: comprehension is not conversion; publish gated; no fake uplift."""
import unittest

import launch
from launch import (AuthorizationRequired, FabricationError, claim_validator,
                    comprehension, decide, publish)


class LaunchTests(unittest.TestCase):
    def test_comprehension_scores_test_sessions(self):
        out = comprehension([
            {'variant': 'A', 'understood': True, 'test_account': True},
            {'variant': 'A', 'understood': False, 'test_account': True},
            {'variant': 'B', 'understood': True, 'test_account': True}])
        self.assertEqual(out['by_variant']['A'], {'n': 2, 'understood': 1})
        self.assertEqual(out['real_users'], 0)
        self.assertIn('NOT conversion', out['metric'])

    def test_real_user_session_refused(self):
        with self.assertRaises(FabricationError):
            comprehension([{'variant': 'A', 'understood': True,
                            'test_account': False}])

    def test_publish_needs_authorization(self):
        with self.assertRaises(AuthorizationRequired):
            publish('landing-page')
        with self.assertRaises(AuthorizationRequired):
            publish('landing-page', authorized=True)
        ok = publish('landing-page', authorized=True, authorizer='owner',
                     scope='local-only draft')
        self.assertEqual(ok['authorizer'], 'owner')

    def test_decide_stops_without_real_users(self):
        memo = decide([{'finding': 'f1', 'supports': 'keep'},
                       {'finding': 'f2', 'supports': 'stop',
                        'conflicts': 'f1'}])
        self.assertTrue(memo['verdict'].startswith('STOP'))
        self.assertEqual(memo['real_users'], 0)
        self.assertEqual(memo['conflicting_feedback_retained'], 1)

    def test_claims_need_real_evidence(self):
        for kind in ('conversion-uplift', 'customer-quote',
                     'business-revenue'):
            with self.assertRaises(FabricationError):
                claim_validator(kind, real_user_evidence=0)
        ok = claim_validator('customer-quote', real_user_evidence=6)
        self.assertIn('n=6', ok['basis'])


if __name__ == '__main__':
    unittest.main()
