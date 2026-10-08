"""P12-04: remediation replay blocks the attacks, preserves legitimate work."""
import unittest

import detect
import evaluate
import groundtruth
import harden
import scenarios


class ControlSemanticsTests(unittest.TestCase):
    def test_r1_denies_password_only_interactive_login(self):
        events, _ = scenarios.logical_events('m01-credstuff-exfil')
        hardened, applied = harden.apply_controls(events)
        denied = [e for e in hardened if e['action'] == 'login_denied_mfa']
        self.assertTrue(denied)
        self.assertTrue(all(e['kind'] == 'failure' for e in denied))
        self.assertTrue(all('R1' in a['controls'] for a in applied
                            if any(e['id'] == a['id'] for e in denied)))

    def test_r1_allows_mfa_and_workload_logins(self):
        for sid in ('b02-password-expiry-retries',  # password+totp
                    'b05-vpn-reconnect-retries',    # password+totp
                    'b01-admin-bulk-restore',       # workload
                    'b03-helpdesk-unlock-burst'):   # workload
            events, _ = scenarios.logical_events(sid)
            hardened, applied = harden.apply_controls(events)
            self.assertEqual(
                [e for e in hardened if e['action'] == 'login_denied_mfa'],
                [], 'R1 must not bite %s' % sid)
            self.assertEqual(applied, [])

    def test_r2_denies_unticketed_bulk_but_keeps_ticketed_and_small(self):
        events, _ = scenarios.logical_events('m02-validcreds-staged-exfil')
        hardened, _ = harden.apply_controls(events)
        denied = [e for e in hardened
                  if e['action'] == 'egress_denied_no_ticket']
        self.assertTrue(denied)
        self.assertTrue(all(e['bytes_out'] == 0 for e in denied))
        # b01 ticketed bulk passes untouched
        events, _ = scenarios.logical_events('b01-admin-bulk-restore')
        hardened, applied = harden.apply_controls(events)
        self.assertEqual(applied, [])
        self.assertTrue(any(e['action'] == 'download' and e['bytes_out'] > 0
                            for e in hardened))
        # b02 small unticketed reads pass untouched
        events, _ = scenarios.logical_events('b02-password-expiry-retries')
        hardened, applied = harden.apply_controls(events)
        self.assertEqual(applied, [])

    def test_ids_seq_omissions_preserved(self):
        for sid in scenarios.SCENARIO_IDS:
            events, _ = scenarios.logical_events(sid)
            hardened, _ = harden.apply_controls(events)
            self.assertEqual([e['id'] for e in hardened],
                             [e['id'] for e in events])
            self.assertEqual([e['seq'] for e in hardened],
                             [e['seq'] for e in events])
            self.assertEqual([e['omit_from_files'] for e in hardened],
                             [e['omit_from_files'] for e in events])

    def test_controls_apply_only_to_malicious(self):
        revealed = groundtruth.reveal(list(scenarios.SCENARIO_IDS))
        for sid in scenarios.SCENARIO_IDS:
            events, _ = scenarios.logical_events(sid)
            _, applied = harden.apply_controls(events)
            if revealed[sid]['malicious']:
                self.assertGreater(len(applied), 0, sid)
            else:
                self.assertEqual(applied, [], sid)


class ReplayIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.mkdtemp(prefix='p12-harden-test-')
        harden.write_hardened_fixtures(cls.tmp)
        cls.orig = evaluate.load_corpus()
        cls.hard = evaluate.load_corpus(root=cls.tmp)
        cls.find_orig = evaluate.run_detectors(cls.orig)
        cls.find_hard = evaluate.run_detectors(cls.hard)

    def _exfil(self, corpus, sid):
        return sum(e.get('bytes_out', 0)
                   for e in corpus[sid]['timeline'].events
                   if e.get('action') in ('download', 'export'))

    def test_detectors_unchanged_across_runs(self):
        self.assertEqual(detect.configuration(), detect.configuration())

    def test_malicious_exfil_blocked(self):
        for sid in ('m01-credstuff-exfil', 'm02-validcreds-staged-exfil',
                    'm03-slow-credstuff', 'm04-insider-known-ip-bulk'):
            self.assertGreater(self._exfil(self.orig, sid), 0)
            self.assertEqual(self._exfil(self.hard, sid), 0, sid)

    def test_benign_exfil_untouched(self):
        for sid in ('b01-admin-bulk-restore', 'b04-quarterly-report-export',
                    'b02-password-expiry-retries'):
            self.assertEqual(self._exfil(self.hard, sid),
                             self._exfil(self.orig, sid), sid)

    def test_no_new_benign_flags(self):
        benign = [s for s in scenarios.SCENARIO_IDS
                  if not groundtruth.reveal([s])[s]['malicious']]
        for sid in benign:
            flagged_orig = {d for d, fl in self.find_orig[sid].items() if fl}
            flagged_hard = {d for d, fl in self.find_hard[sid].items() if fl}
            self.assertLessEqual(flagged_hard, flagged_orig, sid)

    def test_hardened_corpus_differs_only_where_controls_fired(self):
        import json
        from pathlib import Path
        orig_man = json.loads(
            (scenarios.FIXTURE_ROOT / 'manifest.json').read_text())
        hard_man = json.loads(
            (Path(self.tmp) / 'manifest.json').read_text())
        self.assertNotEqual(orig_man['corpus_sha256'],
                            hard_man['corpus_sha256'])
        self.assertEqual(hard_man['controls'], ['R1', 'R2'])


if __name__ == '__main__':
    unittest.main()
