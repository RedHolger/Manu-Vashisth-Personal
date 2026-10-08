"""P11-02: expiry, revocation, unknown/malformed, privilege change — fail closed."""
import unittest

import lab_app
import policy_oracle as oracle
import runner


class ExpiryRevocationTests(unittest.TestCase):
    def test_expired_admin_bypass_detected(self):
        report = runner.evaluate(lab_app.VULNERABLE_BUGS, 'extended')
        hits = [v for v in report['violations']
                if v['label'] == 'expired-admin-bypass']
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['expected_reason'], 'expired')
        self.assertTrue(hits[0]['actual_allow'])

    def test_revoked_admin_bypass_detected(self):
        report = runner.evaluate(lab_app.VULNERABLE_BUGS, 'extended')
        hits = [v for v in report['violations']
                if v['label'] == 'revoked-admin-bypass']
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['expected_reason'], 'revoked')
        self.assertTrue(hits[0]['actual_allow'])

    def test_expired_and_revoked_fail_closed_on_fixed(self):
        report = runner.evaluate(frozenset(), 'extended')
        by_label = {r['label']: r for r in report['records']}
        for label in ('expired-session', 'revoked-session',
                      'expired-admin-bypass', 'revoked-admin-bypass'):
            self.assertFalse(by_label[label]['expected'], label)
            self.assertFalse(by_label[label]['actual_allow'], label)


class UnknownMalformedTests(unittest.TestCase):
    def test_unknown_action_fails_closed_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            row = next(r for r in report['records']
                       if r['label'] == 'unknown-action')
            self.assertFalse(row['expected'])
            self.assertFalse(row['actual_allow'])
            self.assertEqual(row['actual_status'], 405)

    def test_malformed_token_fails_closed_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            row = next(r for r in report['records']
                       if r['label'] == 'malformed-token')
            self.assertFalse(row['expected'])
            self.assertFalse(row['actual_allow'])
            self.assertEqual(row['actual_status'], 401)

    def test_unknown_resource_fails_closed_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            row = next(r for r in report['records']
                       if r['label'] == 'unknown-resource')
            self.assertFalse(row['expected'])
            self.assertFalse(row['actual_allow'])
            self.assertEqual(row['actual_status'], 404)


class PrivilegeChangeTests(unittest.TestCase):
    def test_demotion_removes_delete_reach_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            row = next(r for r in report['records']
                       if r['label'] == 'privilege-demotion-denies')
            self.assertFalse(row['expected'])
            self.assertFalse(row['actual_allow'])

    def test_forged_admin_claim_denied_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            row = next(r for r in report['records']
                       if r['label'] == 'forged-admin-claim-denied')
            self.assertFalse(row['expected'])
            self.assertFalse(row['actual_allow'])

    def test_oracle_ignores_claimed_role(self):
        allow, _ = oracle.expected(oracle.TOKENS['forged_bob_admin'],
                                   'DELETE', 'A', 'doc2')
        self.assertFalse(allow)


class SanitizedEvidenceTests(unittest.TestCase):
    def test_no_bearer_in_extended_reports(self):
        import json
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'extended')
            self.assertNotIn('tok-', json.dumps(report))

    def test_every_record_has_expected_reason(self):
        report = runner.evaluate(frozenset(), 'extended')
        for record in report['records']:
            self.assertIn('expected_reason', record)
            self.assertTrue(record['expected_reason'])


if __name__ == '__main__':
    unittest.main()
