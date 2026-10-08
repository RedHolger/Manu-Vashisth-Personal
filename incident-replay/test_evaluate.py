"""P12-02: ground-truth scoring, the fixed split, and measured false positives."""
import json
import unittest

import detect
import evaluate
import groundtruth
import scenarios

M01 = 'm01-credstuff-exfil'
M02 = 'm02-validcreds-staged-exfil'
M03 = 'm03-slow-credstuff'
M04 = 'm04-insider-known-ip-bulk'
B01 = 'b01-admin-bulk-restore'
B02 = 'b02-password-expiry-retries'
B03 = 'b03-helpdesk-unlock-burst'
B04 = 'b04-quarterly-report-export'
B05 = 'b05-vpn-reconnect-retries'

REFERENCE = detect.REFERENCE_RULE
SEQUENCE = detect.SEQUENCE_RULE


def setUpModule():
    scenarios.write_fixtures()


class SplitTests(unittest.TestCase):
    def test_split_is_disjoint_complete_and_hashed(self):
        partition = scenarios.split()
        self.assertEqual(len(partition['dev']), 5)
        self.assertEqual(len(partition['held_out']), 4)
        self.assertFalse(set(partition['dev']) & set(partition['held_out']))
        self.assertEqual(sorted(partition['dev'] + partition['held_out']),
                         sorted(scenarios.SCENARIO_IDS))
        self.assertEqual(partition['order'],
                         scenarios.split()['order'])

    def test_split_depends_only_on_the_id_string(self):
        self.assertEqual(scenarios.split(seed=7)['dev'],
                         scenarios.split(seed=7)['dev'])
        self.assertNotEqual(scenarios.split(seed=7)['dev'],
                            scenarios.split(seed=11)['dev'])

    def test_both_splits_contain_malicious_and_benign_scenarios(self):
        partition = scenarios.split()
        for name in ('dev', 'held_out'):
            malicious = [sid for sid in partition[name]
                         if groundtruth.is_malicious(sid)]
            benign = [sid for sid in partition[name]
                      if not groundtruth.is_malicious(sid)]
            self.assertTrue(malicious)
            self.assertTrue(benign)

    def test_the_held_out_split_is_the_declared_one(self):
        partition = scenarios.split()
        self.assertEqual(sorted(partition['dev']),
                         sorted([B05, M03, M01, B04, B01]))
        self.assertEqual(sorted(partition['held_out']),
                         sorted([M04, B02, M02, B03]))


class GroundTruthTests(unittest.TestCase):
    def test_annotation_table_is_internally_consistent(self):
        report = groundtruth.integrity_report()
        self.assertEqual(report['problems'], [])
        self.assertEqual(report['scenarios'], 9)
        self.assertEqual(report['malicious'], 4)
        self.assertEqual(report['benign'], 5)
        self.assertEqual(report['attack_events'], 70)
        self.assertEqual(report['absent_events'], 2)

    def test_malicious_and_benign_sets_are_disjoint_and_named(self):
        self.assertEqual(groundtruth.malicious_ids(), [M01, M02, M03, M04])
        self.assertEqual(groundtruth.benign_ids(), [B01, B02, B03, B04, B05])
        for sid in groundtruth.benign_ids():
            self.assertTrue(groundtruth.GROUND_TRUTH[sid][
                'benign_lookalike_of'])
            self.assertTrue(groundtruth.GROUND_TRUTH[sid]['benign_rationale'])
            self.assertEqual(groundtruth.attack_event_ids(sid), [])

    def test_attack_ids_come_from_the_annotated_session(self):
        self.assertEqual(len(groundtruth.attack_event_ids(M01)), 27)
        self.assertEqual(len(groundtruth.attack_event_ids(M02)), 15)
        self.assertEqual(len(groundtruth.attack_event_ids(M03)), 16)
        self.assertEqual(len(groundtruth.attack_event_ids(M04)), 12)
        self.assertIn('m01-000001', groundtruth.attack_event_ids(M01))
        self.assertNotIn('m01-000029', groundtruth.attack_event_ids(M01))

    def test_absent_ids_are_reported_and_never_attack_evidence(self):
        absent = groundtruth.absent_event_ids(M01)
        self.assertEqual(absent, ['m01-000027', 'm01-000028'])
        self.assertFalse(set(absent) & set(groundtruth.attack_event_ids(M01)))
        for sid in scenarios.SCENARIO_IDS:
            self.assertEqual(groundtruth.absent_event_ids(sid),
                             scenarios.absent_event_ids(sid))

    def test_reveal_is_the_only_label_path_and_rejects_unknown_ids(self):
        with self.assertRaises(KeyError):
            groundtruth.reveal(['not-a-scenario'])
        revealed = groundtruth.reveal([M01, B01])
        self.assertEqual(sorted(revealed), [B01, M01])
        self.assertEqual(len(revealed[M01]['attack_event_ids']), 27)
        self.assertEqual(revealed[B01]['attack_event_ids'], [])
        self.assertEqual(revealed[M01]['absent_event_ids'],
                         ['m01-000027', 'm01-000028'])

    def test_the_label_table_is_not_mutable_through_reveal(self):
        copy = groundtruth.labels()
        copy[M01]['malicious'] = False
        copy[M01]['narrative'] = 'tampered'
        self.assertTrue(groundtruth.GROUND_TRUTH[M01]['malicious'])
        self.assertNotEqual(groundtruth.GROUND_TRUTH[M01]['narrative'],
                            'tampered')


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = evaluate.load_corpus()
        cls.findings = evaluate.run_detectors(cls.corpus)
        cls.report = evaluate.evaluate(cls.corpus, cls.findings)

    def test_events_carry_no_label_field(self):
        forbidden = {'malicious', 'label', 'truth', 'attack', 'benign',
                     'ground_truth', 'attack_session', 'y'}
        for entry in self.corpus.values():
            for event in entry['timeline'].events:
                self.assertFalse(forbidden & set(event))

    def test_every_cited_evidence_id_exists_in_its_own_timeline(self):
        for sid, per_detector in self.findings.items():
            ids = self.corpus[sid]['timeline'].ids()
            for name, findings in per_detector.items():
                for finding in findings:
                    self.assertEqual(finding['scenario'], sid)
                    for event_id in finding['evidence_ids']:
                        self.assertIn(event_id, ids)

    def test_no_finding_cites_an_event_that_never_reached_a_source(self):
        for sid, per_detector in self.findings.items():
            absent = set(groundtruth.absent_event_ids(sid))
            for findings in per_detector.values():
                for finding in findings:
                    self.assertFalse(absent & set(finding['evidence_ids']))

    def test_evaluation_is_deterministic(self):
        again = evaluate.evaluate(self.corpus,
                                  evaluate.run_detectors(self.corpus))
        self.assertEqual(json.dumps(again, sort_keys=True),
                         json.dumps(self.report, sort_keys=True))


class ScenarioMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate.evaluate()

    def _scenario(self, name, split='all'):
        return self.report['per_detector'][name]['scenario_level'][split]

    def test_counts_are_exhaustive_for_every_detector_and_split(self):
        for name in (REFERENCE, SEQUENCE, evaluate.COMBINED):
            for split in ('all', 'dev', 'held_out'):
                metrics = self._scenario(name, split)
                self.assertEqual(metrics['tp'] + metrics['fp']
                                 + metrics['fn'] + metrics['tn'],
                                 metrics['n_scenarios'])
                self.assertEqual(metrics['tp'] + metrics['fn'],
                                 metrics['n_malicious'])
                self.assertEqual(metrics['fp'] + metrics['tn'],
                                 metrics['n_benign'])
                self.assertEqual(len(metrics['tp_ids']), metrics['tp'])
                self.assertEqual(len(metrics['fp_ids']), metrics['fp'])
                self.assertEqual(len(metrics['fn_ids']), metrics['fn'])
                self.assertEqual(len(metrics['tn_ids']), metrics['tn'])

    def test_reference_rule_exact_counts_and_ids(self):
        metrics = self._scenario(REFERENCE)
        self.assertEqual((metrics['tp'], metrics['fp'], metrics['fn'],
                          metrics['tn']), (2, 3, 2, 2))
        self.assertEqual(metrics['tp_ids'], [M01, M03])
        self.assertEqual(metrics['fp_ids'], [B02, B03, B05])
        self.assertEqual(metrics['fn_ids'], [M02, M04])
        self.assertEqual(metrics['tn_ids'], [B01, B04])
        self.assertEqual(metrics['precision'], 0.4)
        self.assertEqual(metrics['recall'], 0.5)

    def test_sequence_detector_exact_counts_and_ids(self):
        metrics = self._scenario(SEQUENCE)
        self.assertEqual((metrics['tp'], metrics['fp'], metrics['fn'],
                          metrics['tn']), (3, 0, 1, 5))
        self.assertEqual(metrics['tp_ids'], [M01, M02, M03])
        self.assertEqual(metrics['fp_ids'], [])
        self.assertEqual(metrics['fn_ids'], [M04])
        self.assertEqual(metrics['precision'], 1.0)
        self.assertEqual(metrics['recall'], 0.75)

    def test_ratios_are_arithmetic_consequences_of_the_counts(self):
        for name in (REFERENCE, SEQUENCE, evaluate.COMBINED):
            for split in ('all', 'dev', 'held_out'):
                metrics = self._scenario(name, split)
                positive = metrics['tp'] + metrics['fp']
                actual = metrics['tp'] + metrics['fn']
                expected_precision = (round(metrics['tp'] / positive, 4)
                                      if positive else None)
                expected_recall = (round(metrics['tp'] / actual, 4)
                                   if actual else None)
                self.assertEqual(metrics['precision'], expected_precision)
                self.assertEqual(metrics['recall'], expected_recall)
                self.assertEqual(
                    metrics['accuracy'],
                    round((metrics['tp'] + metrics['tn'])
                          / metrics['n_scenarios'], 4))

    def test_held_out_is_reported_separately_and_is_worse_for_the_rule(self):
        dev = self._scenario(REFERENCE, 'dev')
        held = self._scenario(REFERENCE, 'held_out')
        self.assertEqual((dev['tp'], dev['fp'], dev['fn'], dev['tn']),
                         (2, 1, 0, 2))
        self.assertEqual((held['tp'], held['fp'], held['fn'], held['tn']),
                         (0, 2, 2, 0))
        self.assertEqual(dev['recall'], 1.0)
        self.assertEqual(held['recall'], 0.0)
        self.assertEqual(held['precision'], 0.0)
        seq_held = self._scenario(SEQUENCE, 'held_out')
        self.assertEqual((seq_held['tp'], seq_held['fp'], seq_held['fn'],
                          seq_held['tn']), (1, 0, 1, 2))
        self.assertEqual(seq_held['recall'], 0.5)
        self.assertEqual(seq_held['precision'], 1.0)

    def test_combined_is_exactly_the_union_of_the_two_detectors(self):
        combined = self._scenario(evaluate.COMBINED)
        reference = self._scenario(REFERENCE)
        sequence = self._scenario(SEQUENCE)
        self.assertEqual(set(combined['tp_ids']),
                         set(reference['tp_ids']) | set(sequence['tp_ids']))
        self.assertEqual(set(combined['fp_ids']),
                         set(reference['fp_ids']) | set(sequence['fp_ids']))
        self.assertEqual(set(combined['fn_ids']),
                         set(reference['fn_ids']) & set(sequence['fn_ids']))
        self.assertEqual((combined['tp'], combined['fp'], combined['fn'],
                          combined['tn']), (3, 3, 1, 2))


class FalsePositiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate.evaluate()
        cls.fps = cls.report['benign_lookalike_false_positives']

    def test_every_benign_lookalike_is_accounted_for(self):
        self.assertEqual(sorted(self.fps), groundtruth.benign_ids())
        for sid, entry in self.fps.items():
            self.assertTrue(entry['benign_lookalike_of'])
            self.assertTrue(entry['benign_rationale'])

    def test_the_reference_rule_produces_three_measured_false_positives(self):
        flagged = sorted(sid for sid, entry in self.fps.items()
                         if entry['false_positive'])
        self.assertEqual(flagged, [B02, B03, B05])
        for sid in flagged:
            self.assertEqual(self.fps[sid]['flagged_by'], [REFERENCE])
            self.assertNotIn(SEQUENCE, self.fps[sid]['flagged_by'])

    def test_the_sequence_detector_produces_zero_false_positives(self):
        for sid, entry in self.fps.items():
            self.assertNotIn(SEQUENCE, entry['flagged_by'])
        self.assertEqual(self.report['per_detector'][SEQUENCE][
            'scenario_level']['all']['fp'], 0)

    def test_the_loudest_lookalike_is_not_flagged_by_anything(self):
        entry = self.fps[B01]
        self.assertEqual(entry['flagged_by'], [])
        self.assertFalse(entry['false_positive'])
        self.assertIn('bulk exfiltration', entry['benign_lookalike_of'])

    def test_false_positive_evidence_ids_are_recorded(self):
        evidence = self.fps[B05]['false_positive_evidence_ids'][REFERENCE]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(len(evidence[0]), 7)
        self.assertEqual(evidence[0][0], 'b05-000001')


class EventMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate.evaluate()

    def _event(self, name, split='all'):
        return self.report['per_detector'][name]['event_level'][split]

    def test_annotated_absent_and_citable_attack_events_are_separated(self):
        metrics = self._event(SEQUENCE)
        self.assertEqual(metrics['attack_events_annotated'], 70)
        self.assertEqual(metrics['attack_events_in_evidence'], 70)
        self.assertEqual(metrics['attack_events_absent_from_sources'], 0)

    def test_the_rule_cites_mostly_benign_events_as_its_evidence(self):
        metrics = self._event(REFERENCE)
        self.assertEqual(metrics['evidence_ids_cited'], 35)
        self.assertEqual(metrics['evidence_ids_on_attack'], 17)
        self.assertEqual(metrics['evidence_ids_not_on_attack'], 18)
        self.assertEqual(metrics['evidence_precision'], 0.4857)
        self.assertEqual(metrics['attack_coverage'], 0.2429)

    def test_the_sequence_detector_cites_only_attack_events(self):
        metrics = self._event(SEQUENCE)
        self.assertEqual(metrics['evidence_ids_cited'], 42)
        self.assertEqual(metrics['evidence_ids_on_attack'], 42)
        self.assertEqual(metrics['evidence_ids_not_on_attack'], 0)
        self.assertEqual(metrics['evidence_precision'], 1.0)
        self.assertEqual(metrics['attack_coverage'], 0.6)

    def test_the_missed_scenario_is_visible_at_event_level_too(self):
        per = self._event(SEQUENCE)['per_scenario']
        self.assertEqual(per[M04]['attack_events_annotated'], 12)
        self.assertEqual(len(per[M04]['missed_attack_ids']), 12)
        self.assertEqual(per[M04]['evidence_ids_cited'], 0)

    def test_absent_events_are_listed_per_scenario_not_invented(self):
        for name in (REFERENCE, SEQUENCE, evaluate.COMBINED):
            per = self._event(name)['per_scenario']
            self.assertEqual(per[M01]['attack_events_absent'], [])
        report = evaluate.evaluate()
        self.assertEqual(report['per_detector'][SEQUENCE]['event_level'][
            'all']['attack_events_absent_from_sources'], 0)

    def test_combined_event_precision_sits_between_the_two_detectors(self):
        metrics = self._event(evaluate.COMBINED)
        self.assertEqual(metrics['evidence_ids_on_attack'], 57)
        self.assertEqual(metrics['evidence_ids_not_on_attack'], 18)
        self.assertEqual(metrics['evidence_precision'], 0.76)
        self.assertGreater(metrics['attack_coverage'], 0.8)


if __name__ == '__main__':
    unittest.main()
