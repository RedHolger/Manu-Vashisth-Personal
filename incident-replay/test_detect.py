"""P12-02: the detectors themselves — reference rule reuse and sequence logic."""
import ast
import hashlib
import unittest
from pathlib import Path

import detect
import groundtruth
import ingest
import scenarios
from ingest import Ingestor, to_reference_events
from project import analyze

REFERENCE_SHA256 = ('7bbc332910118cd7b28153a240db0a45166375f75e9304a274fb'
                    '7be8d4fea614')
TEST_CORE_SHA256 = ('ba8bf876b64db5cc1a9e8f6fde8b439a8cdd2dac0e5b3f93043a'
                    'be509e868f3e')

M01 = 'm01-credstuff-exfil'
M02 = 'm02-validcreds-staged-exfil'
M04 = 'm04-insider-known-ip-bulk'
B01 = 'b01-admin-bulk-restore'
B02 = 'b02-password-expiry-retries'
B04 = 'b04-quarterly-report-export'


def setUpModule():
    scenarios.write_fixtures()


def _load(scenario_id):
    timeline = Ingestor().ingest_scenario(scenario_id)
    return timeline, scenarios.load_baseline(scenario_id)


class ReferenceIntegrityTests(unittest.TestCase):
    def test_reference_source_is_byte_identical_to_the_kit(self):
        self.assertEqual(hashlib.sha256(
            Path('project.py').read_bytes()).hexdigest(), REFERENCE_SHA256)
        self.assertEqual(hashlib.sha256(
            Path('test_core.py').read_bytes()).hexdigest(), TEST_CORE_SHA256)
        kit = Path('../portfolio-source-kit/projects/incident-replay')
        if (kit / 'project.py').exists():
            self.assertEqual((kit / 'project.py').read_bytes(),
                             Path('project.py').read_bytes())
            self.assertEqual((kit / 'test_core.py').read_bytes(),
                             Path('test_core.py').read_bytes())

    def test_projection_matches_the_five_key_contract(self):
        timeline, _ = _load(M01)
        projected = to_reference_events(timeline.events)
        for event in projected:
            self.assertEqual(set(event), {'id', 'at', 'user', 'ip', 'kind'})
            self.assertIn(event['kind'], ('failure', 'success'))
        analyze(projected)

    def test_reference_rule_is_delegated_not_reimplemented(self):
        timeline, baseline = _load(M01)
        projected = to_reference_events(timeline.events)
        raw = analyze(projected)['findings']
        wrapped = detect.run_reference(timeline.events, M01, baseline)
        self.assertEqual(len(raw), 1)
        self.assertEqual(len(wrapped), 1)
        self.assertEqual(wrapped[0]['rule'], 'failures_then_success')
        self.assertEqual(wrapped[0]['detector'], detect.REFERENCE_RULE)
        self.assertEqual(wrapped[0]['evidence_ids'], raw[0]['evidence_ids'])
        self.assertEqual(wrapped[0]['confidence'], raw[0]['confidence'])
        self.assertEqual(
            wrapped[0]['detail']['reference_input_sha256'],
            analyze(projected)['input_sha256'])

    def test_reference_ignores_the_data_plane_by_contract(self):
        timeline, baseline = _load(M01)
        findings = detect.run_reference(timeline.events, M01, baseline)
        actions = sum(1 for event in timeline.events
                      if event['kind'] == 'action')
        self.assertEqual(findings[0]['detail']['excluded_data_plane_events'],
                         actions)
        self.assertGreater(actions, 0)
        self.assertTrue(all(event['kind'] in ('failure', 'success')
                            for event in timeline.events
                            if event['id'] in findings[0]['evidence_ids']))


class SequenceDetectorTests(unittest.TestCase):
    def test_catches_a_valid_credential_attack_with_no_failures(self):
        timeline, baseline = _load(M02)
        findings = detect.run_bulk_egress(timeline.events, M02, baseline)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['detector'], detect.SEQUENCE_RULE)
        self.assertEqual(finding['severity'], 'critical')
        self.assertEqual(finding['detail']['bytes_out_total'], 4_800_000_000)
        self.assertEqual(finding['detail']['data_plane_objects'], 12)
        self.assertEqual(finding['detail']['ip_in_baseline'], False)
        self.assertEqual(detect.run_reference(timeline.events, M02, baseline),
                         [])

    def test_baselined_ip_with_larger_volume_is_not_flagged(self):
        timeline, baseline = _load(B01)
        findings = detect.run_bulk_egress(timeline.events, B01, baseline)
        self.assertEqual(findings, [])
        total = sum(event['bytes_out'] for event in timeline.events)
        self.assertEqual(total, 6_000_000_000)
        self.assertGreater(total, 4_800_000_000)

    def test_ticketed_export_below_threshold_is_not_flagged(self):
        timeline, baseline = _load(B04)
        self.assertEqual(detect.run_bulk_egress(timeline.events, B04,
                                                baseline), [])
        self.assertEqual(sum(event['bytes_out']
                             for event in timeline.events), 335_728_640)

    def test_an_unknown_actor_has_no_baseline_so_every_ip_is_new(self):
        timeline, _ = _load(M04)
        findings = detect.run_bulk_egress(timeline.events, M04,
                                          {'users': {}})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['detail']['baseline_known_ips'], [])

    def test_thresholds_are_parameters_not_constants(self):
        timeline, baseline = _load(M01)
        strict = detect.run_bulk_egress(
            timeline.events, M01, baseline,
            egress_threshold_bytes=1_000_000_000)
        self.assertEqual(strict, [])
        loose = detect.run_bulk_egress(timeline.events, M01, baseline,
                                       min_objects=100)
        self.assertEqual(loose, [])
        narrow = detect.run_bulk_egress(timeline.events, M01, baseline,
                                        window_seconds=60)
        self.assertEqual(narrow, [])

    def test_both_detectors_miss_the_baselined_insider(self):
        """The corpus keeps an honest false negative for both detectors."""
        timeline, baseline = _load(M04)
        self.assertEqual(detect.run_reference(timeline.events, M04, baseline),
                         [])
        self.assertEqual(
            detect.run_bulk_egress(timeline.events, M04, baseline), [])
        self.assertEqual(sum(event['bytes_out']
                             for event in timeline.events), 2_500_000_000)


class FindingShapeTests(unittest.TestCase):
    def test_every_finding_cites_ids_that_exist_in_the_source(self):
        for scenario_id in scenarios.SCENARIO_IDS:
            timeline, baseline = _load(scenario_id)
            findings = detect.run_all(timeline.events, scenario_id, baseline)
            for name, per_detector in findings.items():
                for finding in per_detector:
                    self.assertEqual(finding['detector'], name)
                    self.assertEqual(finding['scenario'], scenario_id)
                    self.assertTrue(finding['evidence_ids'])
                    self.assertEqual(len(finding['evidence_ids']),
                                     len(set(finding['evidence_ids'])))
                    for event_id in finding['evidence_ids']:
                        self.assertTrue(timeline.has(event_id))
                    self.assertLessEqual(finding['first_event_at'],
                                         finding['last_event_at'])

    def test_a_finding_without_evidence_is_refused(self):
        with self.assertRaises(ValueError):
            detect._finding('x', 's', 'u', 'i', [], 'low', 'none', {})

    def test_unknown_detector_is_refused(self):
        with self.assertRaises(KeyError):
            detect.run_detector('telepathy', [], 's', {})

    def test_configuration_is_reported_with_the_results(self):
        config = detect.configuration()
        self.assertEqual(sorted(config['detectors']), detect.detector_names())
        self.assertEqual(config['detectors'][detect.REFERENCE_RULE].count(
            'auth failures'), 1)
        self.assertEqual(config['reference_window_seconds'], 300)
        self.assertEqual(config['sequence_egress_threshold_bytes'],
                         500_000_000)
        self.assertEqual(config['detector_kind'][detect.SEQUENCE_RULE],
                         'sequence')
        self.assertEqual(config['detector_kind'][detect.REFERENCE_RULE],
                         'indicator')


class LabelIsolationTests(unittest.TestCase):
    def test_detector_and_ingest_import_no_label_module(self):
        """Import graph, not prose: neither module can reach the labels."""
        for module in (detect, ingest):
            tree = ast.parse(Path(module.__file__).read_text(
                encoding='utf-8'))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
            self.assertNotIn('groundtruth', imported)
            names = {node.id for node in ast.walk(tree)
                     if isinstance(node, ast.Name)}
            names |= {node.attr for node in ast.walk(tree)
                      if isinstance(node, ast.Attribute)}
            for forbidden in ('GROUND_TRUTH', 'reveal', 'is_malicious',
                              'attack_event_ids', 'malicious_ids'):
                self.assertNotIn(forbidden, names)

    def test_inverting_every_label_leaves_findings_identical(self):
        corpus = {sid: _load(sid) for sid in scenarios.SCENARIO_IDS}
        before = {sid: detect.run_all(corpus[sid][0].events, sid,
                                      corpus[sid][1]) for sid in corpus}
        original = {sid: entry['malicious']
                    for sid, entry in groundtruth.GROUND_TRUTH.items()}
        try:
            for entry in groundtruth.GROUND_TRUTH.values():
                entry['malicious'] = not entry['malicious']
            after = {sid: detect.run_all(corpus[sid][0].events, sid,
                                         corpus[sid][1]) for sid in corpus}
        finally:
            for sid, value in original.items():
                groundtruth.GROUND_TRUTH[sid]['malicious'] = value
        self.assertEqual(after, before)
        self.assertEqual(groundtruth.malicious_ids(),
                         ['m01-credstuff-exfil', 'm02-validcreds-staged-exfil',
                          'm03-slow-credstuff', 'm04-insider-known-ip-bulk'])

    def test_detector_signatures_cannot_receive_a_label(self):
        import inspect
        for name in detect.detector_names():
            parameters = inspect.signature(
                detect.DETECTORS[name]).parameters
            self.assertNotIn('label', parameters)
            self.assertNotIn('truth', parameters)
            self.assertNotIn('malicious', parameters)

    def test_run_all_needs_only_events_scenario_and_baseline(self):
        import inspect
        self.assertEqual(
            list(inspect.signature(detect.run_all).parameters),
            ['events', 'scenario', 'baseline', 'names'])

    def test_flagged_helpers_return_scenario_ids_only(self):
        corpus = {sid: _load(sid) for sid in (M01, B02)}
        findings = {sid: detect.run_all(corpus[sid][0].events, sid,
                                        corpus[sid][1])
                    for sid in corpus}
        self.assertEqual(detect.flagged(findings, detect.REFERENCE_RULE),
                         [B02, M01])
        self.assertEqual(detect.flagged(findings, detect.SEQUENCE_RULE),
                         [M01])
        self.assertEqual(detect.union_flagged(findings), [B02, M01])


if __name__ == '__main__':
    unittest.main()
