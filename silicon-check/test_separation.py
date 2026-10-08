"""P21-04: sim/synth/board stay separate; synth + board honestly BLOCKED."""
import unittest
from pathlib import Path

import separation


class SeparationTests(unittest.TestCase):
    @unittest.skipUnless(Path(
        'results/p21-01-toolchain/toolchain-report.json').exists(),
        'needs measure outputs; run the measures first')
    def test_simulation_evidence_verified(self):
        kinds = separation.evidence_kinds()
        self.assertEqual(kinds['simulation']['status'], 'VERIFIED')

    def test_synthesis_blocked_without_toolchain(self):
        probe = separation.probe_synthesis()
        if probe['status'] == 'BLOCKED':
            self.assertIn('yosys', probe['note'])
        else:
            self.assertTrue(probe['available'])

    def test_fpga_blocked_without_equipment(self):
        probe = separation.probe_fpga()
        if probe['status'] == 'BLOCKED':
            self.assertFalse(probe['board_inventoried'])
        else:
            self.assertTrue(probe['board_inventoried'])

    def test_kinds_are_distinct_fields(self):
        kinds = separation.evidence_kinds()
        self.assertEqual(set(kinds), {'simulation', 'synthesis', 'board'})
        self.assertNotEqual(kinds['simulation']['status'],
                            kinds['synthesis']['status'] + '-same')

    def test_no_conflation_in_results(self):
        self.assertEqual(separation.no_conflation('results'), [])

    def test_scan_still_catches_affirmative_plant(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'fake.json').write_text(json.dumps(
                {'note': 'synthesis pass achieved on board'}))
            hits = separation.no_conflation(tmp)
            self.assertTrue(hits)
        # ...while a negated disclaimer in the same shape is exempt.
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'honest.json').write_text(json.dumps(
                {'note': 'simulation success is not silicon sign-off'}))
            self.assertEqual(separation.no_conflation(tmp), [])

    def test_separation_doc_exists_with_sections(self):
        text = Path('SEPARATION.md').read_text(encoding='utf-8')
        for section in ('## 1. Simulation', '## 2. Synthesis',
                        '## 3. Board', 'Non-conflation rule'):
            self.assertIn(section, text)


if __name__ == '__main__':
    unittest.main()
