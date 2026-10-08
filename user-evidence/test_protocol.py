"""P15-01: protocol defines neutral tasks; consent guarantees; tooling pilot."""
import unittest
from pathlib import Path

import protocol


class ProtocolTests(unittest.TestCase):
    def test_protocol_doc_has_required_sections(self):
        text = Path('PROTOCOL.md').read_text(encoding='utf-8')
        ok, reason = protocol.validate_protocol(text)
        self.assertTrue(ok, reason)

    def test_study_tasks_are_neutral(self):
        tasks = protocol.study_tasks()
        self.assertEqual(len(tasks), 6)
        ok, reason = protocol.validate_tasks(tasks)
        self.assertTrue(ok, reason)

    def test_leading_task_rejected(self):
        bad = ['Obviously the stale label shows it, just click there.']
        ok, reason = protocol.validate_tasks(bad)
        self.assertFalse(ok)
        self.assertIn('leading phrase', reason)

    def test_consent_doc_has_guarantees(self):
        text = Path('CONSENT_FORM.md').read_text(encoding='utf-8')
        ok, reason = protocol.validate_consent(text)
        self.assertTrue(ok, reason)

    def test_tooling_pilot_runs_on_synthetic_only(self):
        pilot = protocol.pilot_tooling()
        self.assertEqual(pilot['rows'], 6)
        self.assertEqual(pilot['synthetic_rows'], 6)
        self.assertEqual(pilot['human_rows'], 0)
        self.assertEqual(len(pilot['tasks_covered']), 3)


if __name__ == '__main__':
    unittest.main()
