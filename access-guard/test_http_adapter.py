"""P11-01: independent HTTP adapter detects planted cross-tenant/ownership bugs."""
import unittest

import lab_app
import policy_oracle as oracle
import runner


class OracleTests(unittest.TestCase):
    def test_oracle_does_not_import_target(self):
        with open('policy_oracle.py') as handle:
            source = handle.read()
        self.assertFalse(runner._imports_module(source, 'lab_app'))

    def test_target_does_not_import_oracle(self):
        with open('lab_app.py') as handle:
            source = handle.read()
        self.assertFalse(runner._imports_module(source, 'policy_oracle'))

    def test_admin_cannot_cross_tenant(self):
        allow, reason = oracle.expected(
            oracle.TOKENS['alice_admin'], 'GET', 'B', 'doc1')
        self.assertFalse(allow)
        self.assertEqual(reason, 'cross-tenant')

    def test_owner_id_confusion_denied(self):
        allow, reason = oracle.expected(
            oracle.TOKENS['bob_member'], 'GET', 'B', 'doc2')
        self.assertFalse(allow)
        self.assertEqual(reason, 'cross-tenant')

    def test_owner_read_write_allowed(self):
        for method in ('GET', 'POST'):
            allow, _ = oracle.expected(
                oracle.TOKENS['bob_member'], method, 'A', 'doc2')
            self.assertTrue(allow)

    def test_delete_requires_admin(self):
        allow, reason = oracle.expected(
            oracle.TOKENS['bob_member'], 'DELETE', 'A', 'doc2')
        self.assertFalse(allow)
        self.assertEqual(reason, 'delete-requires-admin')
        allow, _ = oracle.expected(
            oracle.TOKENS['alice_admin'], 'DELETE', 'A', 'doc2')
        self.assertTrue(allow)

    def test_unknown_action_denied(self):
        allow, reason = oracle.expected(
            oracle.TOKENS['alice_admin'], 'PUT', 'A', 'doc1')
        self.assertFalse(allow)
        self.assertEqual(reason, 'unknown-action')

    def test_malformed_tokens_denied(self):
        for bad in oracle.MALFORMED_TOKENS + [None, 123]:
            allow, _ = oracle.expected(bad, 'GET', 'A', 'doc1')
            self.assertFalse(allow)


class HttpAdapterTests(unittest.TestCase):
    def test_vulnerable_detects_cross_tenant(self):
        report = runner.evaluate(lab_app.VULNERABLE_BUGS, 'focus')
        cross = [v for v in report['violations']
                 if v['expected_reason'] == 'cross-tenant']
        self.assertGreaterEqual(len(cross), 2)
        labels = {v['label'] for v in cross}
        self.assertIn('attack-admin-cross-tenant-read', labels)
        self.assertIn('attack-owner-id-confusion', labels)

    def test_vulnerable_detects_ownership(self):
        report = runner.evaluate(lab_app.VULNERABLE_BUGS, 'focus')
        own = [v for v in report['violations']
               if v['expected_reason'] == 'not-owner-or-admin']
        self.assertGreaterEqual(len(own), 1)
        self.assertIn('attack-member-write-others',
                      {v['label'] for v in own})

    def test_fixed_variant_is_clean(self):
        report = runner.evaluate(frozenset(), 'focus')
        self.assertEqual(report['mismatches'], 0)

    def test_happy_path_allowed_on_both(self):
        for bugs in (lab_app.VULNERABLE_BUGS, frozenset()):
            report = runner.evaluate(bugs, 'focus')
            happy = [r for r in report['records']
                     if r['label'] in ('admin-read-own', 'owner-read-own',
                                       'owner-write-own', 'admin-delete-own',
                                       'member-read-own-tenant')]
            self.assertTrue(happy)
            self.assertTrue(all(r['expected'] and r['actual_allow']
                                for r in happy))

    def test_records_carry_no_token_secret(self):
        report = runner.evaluate(lab_app.VULNERABLE_BUGS, 'focus')
        import json
        blob = json.dumps(report)
        self.assertNotIn('tok-', blob)
        for record in report['records']:
            self.assertNotIn('token', record)


if __name__ == '__main__':
    unittest.main()
