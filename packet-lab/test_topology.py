"""P19-01/02: admin guard refuses outside; fixtures reset byte-identical."""
import unittest

import scenarios
import topology
from topology import BlockedError, Refused


class TopologyTests(unittest.TestCase):
    def test_allowlisted_dry_run(self):
        op = topology.admin_op('lab-h1', 'capture')
        self.assertFalse(op['executed'])
        self.assertIn('dry-run', op['mode'])

    def test_outside_targets_refused(self):
        for target in ('prod-db', '8.8.8.8', 'lab-h1.evil.com', ''):
            with self.assertRaises(Refused):
                topology.admin_op(target, 'capture')

    def test_unknown_action_refused(self):
        with self.assertRaises(Refused):
            topology.admin_op('lab-h1', 'scan')

    def test_model_baseline_labeled_not_live(self):
        base = topology.healthy_baseline()
        self.assertTrue(base['healthy'])
        self.assertIn('MODEL', base['kind'])
        self.assertEqual(base['topology_version'], 'v1')

    def test_live_topology_blocked(self):
        with self.assertRaises(BlockedError):
            topology.live_topology()


class ScenarioTests(unittest.TestCase):
    def test_four_cases_with_ground_truth(self):
        self.assertEqual(set(scenarios.CASES),
                         {'dns-fail', 'route-blackhole', 'mtu-clamp',
                          'conn-timeout'})
        for case in scenarios.CASES:
            self.assertTrue(scenarios.fixture(case))
            truth = scenarios.GROUND_TRUTH[case]
            self.assertIn(truth['layer'], ('dns', 'route', 'tcp',
                                           'application'))

    def test_reset_reproducible(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            manifest = scenarios.write_fixtures(tmp)
            check = scenarios.reset_check(tmp)
            self.assertTrue(check['reset_reproducible'])
            self.assertEqual(check['corpus_sha256'],
                             manifest['corpus_sha256'])

    def test_documentation_ips_only(self):
        import ipaddress
        for case in scenarios.CASES:
            for line in scenarios.fixture(case):
                for token in line.split():
                    if token.startswith(('src=', 'dst=')):
                        ip = ipaddress.ip_address(token.split('=')[1])
                        self.assertTrue(ip.is_private)


if __name__ == '__main__':
    unittest.main()
