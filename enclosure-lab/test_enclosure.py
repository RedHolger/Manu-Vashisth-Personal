"""P22-02/03: parametric CAD, drawings, comparison without validation claims."""
import unittest
from pathlib import Path

import compare
import enclosure
from enclosure import (bom, check_cutouts, check_fit, check_lid, drawing_svg,
                       enclosure_params, revision_history, scad_v1, scad_v2)


class EnclosureTests(unittest.TestCase):
    def test_outer_math(self):
        p = enclosure_params()
        self.assertAlmostEqual(p['outer_width'], 85 + 2 * (2 + 2))
        self.assertAlmostEqual(p['outer_length'], 56 + 2 * (2 + 2))

    def test_scad_v1_open_top(self):
        text = scad_v1()
        self.assertIn('difference()', text)
        self.assertIn('cube(', text)

    def test_scad_v2_lid_bosses_cutouts(self):
        text = scad_v2()
        self.assertIn('module base()', text)
        self.assertIn('module lid()', text)
        self.assertIn('keep-out A', text)
        self.assertIn('keep-out B', text)
        self.assertIn('cylinder(', text)

    def test_bom_counts(self):
        self.assertEqual(len(bom('v1')), 2)   # base + standoffs
        self.assertGreater(len(bom('v2')), len(bom('v1')))

    def test_fit_cutouts_lid(self):
        fit = check_fit()
        self.assertTrue(fit['ok'])
        self.assertGreaterEqual(fit['clear_x'], 4.0)
        self.assertTrue(check_cutouts()['ok'])
        self.assertTrue(check_lid()['ok'])

    def test_drawing_has_dims_and_assumed_title(self):
        svg = drawing_svg()
        self.assertTrue(svg.startswith('<svg'))
        self.assertIn('ASSUMED', svg)
        self.assertIn('NOT', svg)
        self.assertIn('outer', svg)

    def test_revision_history(self):
        revs = revision_history()
        self.assertEqual([r['rev'] for r in revs], ['v1', 'v2'])


class CompareFitTests(unittest.TestCase):
    def test_compare_structure(self):
        out = compare.compare_revisions()
        self.assertIn('fit', out)
        self.assertIn('assembly', out)
        self.assertIn('thermal', out)
        self.assertFalse(out['fit']['authoritative'])
        self.assertIn('ASSUMED', out['thermal']['v2_assumption'])

    def test_comparison_doc_scans_clean(self):
        text = Path('COMPARISON.md').read_text(encoding='utf-8')
        self.assertEqual(compare.banned_claim_scan(text), [])

    def test_banned_scan_catches_affirmative_plant(self):
        hits = compare.banned_claim_scan(
            'The enclosure fit was validated by thermal simulation passed.')
        self.assertTrue(hits)

    def test_fit_worksheet_blank_and_blocked(self):
        from fit_check import BlockedError, FitWorksheet
        ws = FitWorksheet()
        self.assertTrue(all(r['value'] is None for r in ws.blank()))
        with self.assertRaises(BlockedError):
            ws.verify_fit()

    def test_record_then_verify_is_measured_vs_assumed(self):
        from fit_check import FitWorksheet
        ws = FitWorksheet()
        ws.record('outer_width', 93.1, 'caliper', '2026-10-08T00:00:00Z')
        out = ws.verify_fit()
        self.assertIn('MEASURED_VS_ASSUMED', out['status'])
        self.assertEqual(out['n_measured'], 1)


if __name__ == '__main__':
    unittest.main()
