"""P08-04: external CSV adapter works; no real stream is claimed."""
import json
import unittest
from pathlib import Path

from ingest import connect, ingest, set_segments
from real_data import coverage_note, load_csv_events, write_manifest
from segments import segment_cohorts

HERE = Path(__file__).parent
SAMPLE = HERE / 'sample_events.csv'


class RealDataTests(unittest.TestCase):
    def test_sample_loads_and_matches_kernel(self):
        events, segments = load_csv_events(SAMPLE)
        self.assertEqual(len(events), 4)
        self.assertEqual(segments, {'demo-u1': 'organic',
                                   'demo-u2': 'paid'})
        conn = connect()
        ingest(conn, events)
        set_segments(conn, segments)
        table = segment_cohorts(events, '2026-01-20T00:00:00Z',
                                segments)['cohorts']
        self.assertEqual(table[('2026-01-05', 'organic')]['users'], 1)
        self.assertEqual(table[('2026-01-05', 'paid')]['users'], 1)

    def test_manifest_freezes_provenance(self):
        manifest = write_manifest(SAMPLE, 'synthetic-sample Shayne Daniels',
                                  'Synthetic example — no license needed',
                                  '2026-10-08T00:00:00Z',
                                  HERE / 'sample-manifest.check.json')
        try:
            self.assertEqual(manifest['rows'], 4)
            self.assertEqual(manifest['users'], 2)
            self.assertEqual(len(manifest['sha256']), 64)
            self.assertIn('2026-01-05', manifest['min_at'])
            note = coverage_note(manifest)
            self.assertIn('4 events', note)
            self.assertIn('pseudonymous', note)
        finally:
            (HERE / 'sample-manifest.check.json').unlink(missing_ok=True)

    def test_bad_csv_rejected(self):
        bad = HERE / 'bad.check.csv'
        try:
            bad.write_text('id,user,type,at,ingested_at\n'
                           ',u1,signup,2026-01-05T10:00:00Z,'
                           '2026-01-05T10:00:00Z\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_csv_events(bad)
            bad.write_text('id,user,type,at,ingested_at\n'
                           'e1,u1,click,2026-01-05T10:00:00Z,'
                           '2026-01-05T10:00:00Z\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_csv_events(bad)
            bad.write_text('id,user,type,at,ingested_at\n'
                           'e1,u1,signup,2026-01-05,2026-01-05\n',
                           encoding='utf-8')
            with self.assertRaises(ValueError):
                load_csv_events(bad)
        finally:
            bad.unlink(missing_ok=True)

    def test_no_real_stream_claimed(self):
        source = (HERE / 'DATA_SOURCE.md').read_text(encoding='utf-8')
        self.assertIn('no authorized product event stream', source.lower())
        self.assertIn('Privacy', source)
        self.assertIn('Retention', source)
        self.assertIn('Limitations', source)
        self.assertIn('synthetic adapter example', source.lower())


if __name__ == '__main__':
    unittest.main()
