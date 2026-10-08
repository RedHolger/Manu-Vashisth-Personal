"""P12-03: findings are evidence-linked, and facts/hypotheses stay separate."""
import hashlib
import json
import unittest
from pathlib import Path

import evaluate
import groundtruth
import report
import scenarios
import os

M01 = 'm01-credstuff-exfil'
M04 = 'm04-insider-known-ip-bulk'


def setUpModule():
    scenarios.write_fixtures()



MEASURE_ARTIFACT_PRESENT = os.path.exists(
    'results/p12-02-groundtruth/metrics.json')
MEASURE_GATE = unittest.skipUnless(
    MEASURE_ARTIFACT_PRESENT,
    'needs measure outputs; run measure_p12_02.py first')

class _Fixture(unittest.TestCase):
    """Build the corpus, evaluation and findings once per class."""

    @classmethod
    def setUpClass(cls):
        cls.corpus = evaluate.load_corpus()
        cls.evaluation = evaluate.evaluate(
            cls.corpus, evaluate.run_detectors(cls.corpus))
        cls.findings = report.build_findings(cls.corpus, cls.evaluation)
        cls.validation = report.validate_findings(cls.findings, cls.corpus)
        cls.by_id = {finding['id']: finding for finding in cls.findings}


class ClassificationTests(_Fixture):
    @MEASURE_GATE
    def test_validation_passes_on_the_generated_report(self):
        self.assertTrue(self.validation['ok'], self.validation['problems'])
        self.assertEqual(self.validation['problems'], [])

    def test_the_three_classifications_are_populated_and_disjoint(self):
        counts = self.validation['counts']
        self.assertEqual(counts, {'FACT': 17, 'HYPOTHESIS': 5,
                                  'REMEDIATION': 6})
        self.assertEqual(self.validation['findings'], 28)
        self.assertTrue(self.validation['ids_are_disjoint'])
        prefixes = {finding['id'].split('-')[0]
                    for finding in self.findings}
        self.assertEqual(prefixes, {'FAC', 'HYP', 'REM'})
        for finding in self.findings:
            self.assertTrue(finding['id'].startswith(
                finding['classification'][:3].upper()))

    def test_classification_is_a_labeled_field_not_a_section_convention(self):
        for finding in self.findings:
            self.assertIn(finding['classification'], report.CLASSIFICATIONS)
            self.assertIn('classification', finding)
            self.assertTrue(finding['reproduce'].endswith(finding['id']))

    def test_remediation_is_never_presented_as_evidence_of_a_fix(self):
        for finding in self.findings:
            if finding['classification'] == report.REMEDIATION:
                self.assertEqual(finding['validation_status'],
                                 report.NOT_VALIDATED)
                self.assertNotIn('fixed', finding['statement'].lower())
                self.assertNotIn('resolved', finding['statement'].lower())


class EvidenceLinkTests(_Fixture):
    def test_every_fact_cites_event_ids_that_exist_in_the_timeline(self):
        facts = [f for f in self.findings
                 if f['classification'] == report.FACT]
        cited = 0
        for finding in facts:
            if not finding['evidence_event_ids']:
                continue
            for event_id in finding['evidence_event_ids']:
                owner = finding['scenario'] or next(
                    sid for sid in self.corpus
                    if self.corpus[sid]['timeline'].has(event_id))
                self.assertTrue(self.corpus[owner]['timeline'].has(event_id))
                cited += 1
        self.assertEqual(cited, sum(
            len(f['evidence_event_ids']) for f in facts
            if f['evidence_event_ids']))
        self.assertEqual(cited, 111)

    def test_no_finding_cites_an_event_that_never_reached_a_source(self):
        absent = {event_id for sid in self.corpus
                  for event_id in groundtruth.absent_event_ids(sid)}
        self.assertEqual(absent, {'m01-000027', 'm01-000028'})
        for finding in self.findings:
            self.assertFalse(absent & set(finding['evidence_event_ids']))
            for block in finding['evidence']:
                self.assertFalse(absent & set(block['event_ids']))

    def test_every_cited_sha256_matches_the_bytes_on_disk(self):
        seen = set()
        for finding in self.findings:
            for block in finding['evidence']:
                path = Path(block['source_file'])
                self.assertTrue(path.exists())
                self.assertEqual(
                    block['source_sha256'],
                    hashlib.sha256(path.read_bytes()).hexdigest())
                seen.add(block['source_sha256'])
        self.assertEqual(seen, set(self.validation['cited_source_sha256'])
                         if 'cited_source_sha256' in self.validation
                         else seen)
        self.assertEqual(len(seen), self.validation['cited_source_files'])

    def test_every_cited_event_id_sits_on_the_line_it_claims(self):
        checked = 0
        for finding in self.findings:
            for block in finding['evidence']:
                lines = Path(block['source_file']).read_text(
                    encoding='utf-8').splitlines()
                for event_id, line_no in zip(block['event_ids'],
                                             block['source_lines']):
                    self.assertGreaterEqual(line_no, 1)
                    self.assertLessEqual(line_no, len(lines))
                    self.assertIn(event_id, lines[line_no - 1])
                    checked += 1
        # 249 (id, line) citations resolve; 248 distinct ids per finding,
        # because REM-05 reuses an m01 id already cited by FAC-13/FAC-14.
        self.assertEqual(checked, 249)
        self.assertEqual(self.validation['cited_event_ids'], 248)

    @MEASURE_GATE
    def test_measurement_only_facts_cite_a_checksummed_artifact(self):
        measured = [f for f in self.findings
                    if f['classification'] == report.FACT
                    and not f['evidence_event_ids']]
        self.assertTrue(measured)
        for finding in measured:
            self.assertTrue(finding['measurement'])
            for block in finding['measurement']:
                self.assertTrue(block['exists'])
                path = Path(block['artifact'])
                self.assertEqual(
                    block['sha256'],
                    hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertTrue(block['values'])

    def test_resolve_evidence_reproduces_a_finding_from_raw_sources(self):
        for finding in self.findings:
            resolved = report.resolve_evidence(finding, self.corpus)
            self.assertEqual(resolved['finding_id'], finding['id'])
            for block in resolved['evidence_blocks']:
                self.assertTrue(block['sha256_matches'])
                for row in block['lines']:
                    self.assertIsNotNone(row['raw_line'])
                    self.assertIn(row['event_id'], row['raw_line'])
            for block in resolved['measurement_blocks']:
                if block['exists']:
                    self.assertTrue(block['sha256_matches'])


class TamperTests(_Fixture):
    """Validation must fail when a citation stops matching reality."""

    def _copy(self, finding_id):
        return json.loads(json.dumps(self.by_id[finding_id]))

    def test_a_cited_event_id_that_does_not_exist_is_caught(self):
        broken = self._copy('FAC-01')
        broken['evidence'][0]['event_ids'].append('m01-999999')
        broken['evidence'][0]['source_lines'].append(1)
        broken['evidence_event_ids'].append('m01-999999')
        result = report.validate_findings(
            [broken] + [f for f in self.findings if f['id'] != 'FAC-01'],
            self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('m01-999999' in problem
                            for problem in result['problems']))

    def test_a_wrong_sha256_is_caught(self):
        broken = self._copy('FAC-02')
        broken['evidence'][0]['source_sha256'] = '0' * 64
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('does not match' in problem
                            for problem in result['problems']))

    def test_a_missing_measurement_artifact_is_caught(self):
        broken = self._copy('FAC-15')
        broken['measurement'][0]['artifact'] = 'results/nope/metrics.json'
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('does not exist' in problem
                            for problem in result['problems']))

    def test_a_hypothesis_without_risk_rationale_is_caught(self):
        broken = self._copy('HYP-01')
        broken['risk_rationale'] = ''
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('risk_rationale' in problem
                            for problem in result['problems']))

    def test_a_hypothesis_without_an_alternative_is_caught(self):
        broken = self._copy('HYP-02')
        broken['alternatives'] = []
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('alternative' in problem
                            for problem in result['problems']))

    def test_a_remediation_addressing_nothing_is_caught(self):
        broken = self._copy('REM-01')
        broken['addresses'] = ['FAC-99']
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])
        self.assertTrue(any('FAC-99' in problem
                            for problem in result['problems']))

    def test_a_remediation_without_steps_is_caught(self):
        broken = self._copy('REM-03')
        broken['remediation_steps'] = []
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])

    def test_a_fact_with_no_citation_at_all_is_caught(self):
        broken = self._copy('FAC-01')
        broken['evidence'] = []
        broken['evidence_event_ids'] = []
        broken['measurement'] = []
        result = report.validate_findings([broken], self.corpus)
        self.assertFalse(result['ok'])


class RenderingTests(_Fixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.executive = report.render_executive(cls.findings, cls.evaluation,
                                                cls.corpus)
        cls.technical = report.render_technical(cls.findings, cls.evaluation,
                                                cls.corpus)

    def test_both_reports_name_every_finding(self):
        for finding in self.findings:
            self.assertIn(finding['id'], self.executive)
            self.assertIn(finding['id'], self.technical)
            self.assertIn(finding['title'], self.technical)

    def test_technical_report_cites_event_ids_and_checksums(self):
        cited = {event_id for finding in self.findings
                 for event_id in finding['evidence_event_ids']}
        sha = {block['source_sha256'] for finding in self.findings
               for block in finding['evidence']}
        present = sum(1 for event_id in cited
                      if event_id in self.technical)
        self.assertEqual(present, len(cited))
        for digest in sha:
            self.assertIn(digest, self.technical)
        self.assertEqual(len(sha), 8)

    def test_facts_and_hypotheses_occupy_separate_sections(self):
        markers = ['## 4.1 Fact findings', '## 4.2 Hypothesis findings',
                   '## 4.3 Remediation findings']
        positions = [self.technical.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        bounds = positions + [len(self.technical)]
        for index, classification in enumerate(report.CLASSIFICATIONS):
            section = self.technical[bounds[index]:bounds[index + 1]]
            for finding in self.findings:
                if finding['classification'] == classification:
                    self.assertIn('### %s —' % finding['id'], section)
                else:
                    self.assertNotIn('### %s —' % finding['id'], section)

    def test_executive_is_shorter_and_decision_shaped(self):
        self.assertLess(len(self.executive), len(self.technical))
        self.assertLess(len(self.executive), 8000)
        for heading in ('## Bottom line', '## What we know (facts)',
                        '## What we believe (hypotheses, not facts)',
                        '## What to do (remediation proposals',
                        '## Measured detection performance',
                        '## What this report does not claim'):
            self.assertIn(heading, self.executive)

    def test_reports_disclaim_invented_time_savings(self):
        import re
        for text in (self.executive, self.technical):
            self.assertIn('Synthetic', text)
            self.assertRegex(
                text, r'[Nn]o (analyst|human) time was measured')
            self.assertRegex(text, r'hours saved')
            # No quantified effort or saving anywhere in either report.
            self.assertIsNone(re.search(
                r'\d+(\.\d+)?\s*(analyst\s*)?(hours?|minutes|person-days)',
                text, re.IGNORECASE))
            self.assertIsNone(re.search(
                r'(sav(es|ed|ing)|reduc\w+)\s+\d+\s*(hours?|minutes)',
                text, re.IGNORECASE))

    def test_the_missed_scenario_is_named_in_both_reports(self):
        self.assertIn(M04, self.executive)
        self.assertIn(M04, self.technical)
        self.assertIn('false negative', self.executive.lower())

    def test_reports_are_deterministic(self):
        again = report.build_findings(self.corpus, self.evaluation)
        self.assertEqual(json.dumps(again, sort_keys=True),
                         json.dumps(self.findings, sort_keys=True))
        self.assertEqual(report.render_executive(again, self.evaluation,
                                                 self.corpus),
                         self.executive)
        self.assertEqual(report.render_technical(again, self.evaluation,
                                                 self.corpus),
                         self.technical)


class CommandLineTests(_Fixture):
    @MEASURE_GATE
    def test_the_p12_02_artifact_the_reports_cite_exists(self):
        path = Path(report.EVALUATION_ARTIFACT)
        self.assertTrue(path.exists(),
                        'run measure_p12_02.py before report.py')
        self.assertEqual(len(hashlib.sha256(
            path.read_bytes()).hexdigest()), 64)

    def test_write_reports_creates_three_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            written = report.write_reports(temporary, self.findings,
                                           self.evaluation, self.corpus)
            for key in ('executive', 'technical', 'findings'):
                self.assertTrue(Path(written[key]).exists())
            loaded = json.loads(
                Path(written['findings']).read_text(encoding='utf-8'))
            self.assertEqual(len(loaded), 28)
            self.assertEqual(written['executive_bytes'],
                             len(Path(written['executive']).read_text(
                                 encoding='utf-8')))
            self.assertEqual(written['technical_bytes'],
                             len(Path(written['technical']).read_text(
                                 encoding='utf-8')))

    def test_main_lists_findings_and_resolves_one(self):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(report.main(['--list']), 0)
            self.assertEqual(report.main(['--finding', 'FAC-01']), 0)
            self.assertEqual(report.main(['--finding', 'NOPE-99']), 2)
        printed = buffer.getvalue()
        self.assertIn('FAC-01', printed)
        self.assertIn('"sha256_matches": true', printed)
        self.assertIn('unknown finding', printed)


if __name__ == '__main__':
    unittest.main()
