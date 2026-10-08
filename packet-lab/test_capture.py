"""P19-03/04: bytes map to flows, secrets redacted, runbook keeps wrong turns."""
import unittest

import capture
import runbook
import scenarios
from runbook import UnmeasuredError


class CaptureTests(unittest.TestCase):
    def test_fixture_bytes_map_to_flows(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            parsed = capture.parse_file('%s/mtu-clamp.pkt' % tmp)
        self.assertEqual(parsed['n_packets'], 3)
        self.assertEqual(parsed['rejected'], [])
        total = sum(f['bytes'] for f in parsed['flows'])
        self.assertEqual(total, 64 + 1500 + 128)
        self.assertEqual(parsed['protocol_bytes']['TCP'], 64 + 1500)

    def test_secrets_redacted_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            parsed = capture.parse_file('%s/mtu-clamp.pkt' % tmp)
        self.assertTrue(any(p['secret'] == '[redacted]'
                            for p in parsed['packets']))
        self.assertTrue(capture.secrets_absent(parsed))

    def test_malformed_reported_not_dropped_silently(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'bad.pkt')
            path.write_text('ts=x src=1.1.1.1 dst=2.2.2.2 proto=TCP bytes=10\n'
                            'this is not a packet\n'
                            'ts=x src=bad dst=2.2.2.2 proto=TCP bytes=10\n')
            parsed = capture.parse_file(str(path))
        self.assertEqual(parsed['n_packets'], 1)
        self.assertEqual(len(parsed['rejected']), 2)
        self.assertTrue(all('reason' in r for r in parsed['rejected']))

    def test_provenance_sha_recorded(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            parsed = capture.parse_file('%s/dns-fail.pkt' % tmp)
        self.assertEqual(len(parsed['sha256']), 64)


class RunbookTests(unittest.TestCase):
    def test_troubleshoot_keeps_wrong_hypothesis(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            out = runbook.troubleshoot('mtu-clamp', tmp)
        self.assertEqual(out['wrong_retained'], 1)
        self.assertEqual(len(out['hypotheses']), 2)
        self.assertEqual(out['hypotheses'][0]['verdict'], 'refuted')
        self.assertEqual(out['hypotheses'][1]['verdict'], 'confirmed')
        self.assertEqual(out['ground_truth']['layer'], 'tcp')

    def test_collection_measured_reasoning_blocked(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            out = runbook.troubleshoot('dns-fail', tmp)
        self.assertGreater(out['timing']['collection_seconds_measured'], 0)
        self.assertEqual(out['timing']['reasoning_status'],
                         'BLOCKED_NO_ANALYST_TIMING')
        timing = runbook.Timing()
        with self.assertRaises(UnmeasuredError):
            timing.record_reasoning()

    def test_layers_distinguished(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scenarios.write_fixtures(tmp)
            layers = {c: runbook.troubleshoot(c, tmp)['ground_truth']['layer']
                      for c in scenarios.CASES}
        self.assertEqual(set(layers.values()),
                         {'dns', 'route', 'tcp', 'application'})


if __name__ == '__main__':
    unittest.main()
