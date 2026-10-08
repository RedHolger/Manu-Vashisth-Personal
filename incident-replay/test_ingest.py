"""P12-01: two-format ingestion, provenance, timezone/dedup/skew/gap handling."""
import datetime as dt
import hashlib
import json
import unittest
from pathlib import Path

import scenarios
from ingest import (ADAPTERS, ConflictingEventError, Ingestor,
                    NaiveTimestampError, UnknownFormatError, detect_format,
                    parse_timestamp, sha256_file, to_reference_events)
from project import analyze

ROOT = scenarios.FIXTURE_ROOT
M01 = 'm01-credstuff-exfil'
B01 = 'b01-admin-bulk-restore'


def setUpModule():
    scenarios.write_fixtures()


class TimestampTests(unittest.TestCase):
    def test_explicit_offsets_normalize_to_the_same_utc_instant(self):
        utc, offset, assumed = parse_timestamp('2026-01-04T09:00:00+00:00')
        jst, joffset, jassumed = parse_timestamp('2026-01-04T18:00:00+09:00')
        self.assertEqual(utc, jst)
        self.assertEqual((offset, joffset), (0, 540))
        self.assertFalse(assumed or jassumed)

    def test_zulu_suffix_is_accepted(self):
        when, offset, assumed = parse_timestamp('2026-01-04T09:00:00Z')
        self.assertEqual(offset, 0)
        self.assertFalse(assumed)
        self.assertEqual(when.tzinfo, dt.timezone.utc)

    def test_naive_timestamp_without_declaration_is_refused(self):
        with self.assertRaises(NaiveTimestampError):
            parse_timestamp('2026-01-04T09:00:00')

    def test_declared_offset_is_marked_as_an_assumption(self):
        when, offset, assumed = parse_timestamp('2026-01-04T09:13:22',
                                                declared_utc_offset_minutes=-300)
        self.assertTrue(assumed)
        self.assertEqual(offset, -300)
        self.assertEqual(when.isoformat(), '2026-01-04T14:13:22+00:00')

    def test_garbage_timestamp_is_refused_not_guessed(self):
        for text in ('', '   ', 'not-a-date', '2026-13-45T99:99:99'):
            with self.assertRaises(NaiveTimestampError):
                parse_timestamp(text)


class AdapterTests(unittest.TestCase):
    def test_two_formats_are_registered_with_distinct_ranks(self):
        self.assertEqual(set(ADAPTERS), {'json-audit', 'syslog-kv'})
        self.assertNotEqual(ADAPTERS['json-audit'].source_rank,
                            ADAPTERS['syslog-kv'].source_rank)

    def test_format_detection_and_appledouble_refusal(self):
        self.assertEqual(detect_format('x/audit.jsonl'), 'json-audit')
        self.assertEqual(detect_format('x/edge-syslog.log'), 'syslog-kv')
        with self.assertRaises(UnknownFormatError):
            detect_format('x/._audit.jsonl')
        with self.assertRaises(UnknownFormatError):
            detect_format('x/capture.pcap')

    def test_both_adapters_agree_on_the_same_event(self):
        events, _ = scenarios.logical_events(M01)
        target = next(event for event in events if event['kind'] == 'failure')
        record = scenarios._json_record(target)
        line = scenarios.syslog_line(target)
        json_event = ADAPTERS['json-audit']().parse_line(
            json.dumps(record, sort_keys=True), 1)
        syslog_event = ADAPTERS['syslog-kv']().parse_line(line, 1)
        self.assertEqual(json_event['id'], syslog_event['id'])
        self.assertEqual(json_event['user'], syslog_event['user'])
        self.assertEqual(json_event['kind'], syslog_event['kind'])
        self.assertEqual(json_event['seq'], syslog_event['seq'])
        self.assertNotEqual(json_event['tz_offset_minutes'],
                            syslog_event['tz_offset_minutes'])
        self.assertEqual(
            (syslog_event['at'] - json_event['at']).total_seconds(),
            scenarios.FORWARDER_SKEW_SECONDS)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Ingestor().ingest_corpus()

    def test_every_source_file_carries_a_matching_sha256(self):
        rows = self.timeline.manifest['files']
        self.assertEqual(len(rows), 13)
        for row in rows:
            self.assertEqual(len(row['sha256']), 64)
            self.assertEqual(row['sha256'], sha256_file(row['path']))
            self.assertEqual(row['sha256'],
                             hashlib.sha256(Path(row['path']).read_bytes()
                                            ).hexdigest())

    def test_manifest_is_reproducible_across_runs(self):
        again = Ingestor().ingest_corpus()
        self.assertEqual(again.manifest['corpus_sha256'],
                         self.timeline.manifest['corpus_sha256'])
        self.assertEqual(again.events, self.timeline.events)
        self.assertEqual(len(again.manifest['corpus_sha256']), 64)

    def test_events_carry_their_own_provenance(self):
        for event in self.timeline.events:
            self.assertEqual(len(event['source_sha256']), 64)
            self.assertGreaterEqual(event['source_line'], 1)
            self.assertIn(event['source_format'], ADAPTERS)
            self.assertTrue(event['at'].endswith('+00:00'))

    def test_ingest_does_not_depend_on_file_order(self):
        paths = [row['path'] for row in self.timeline.manifest['files']]
        shuffled = Ingestor().ingest(list(reversed(paths)))
        self.assertEqual([e['id'] for e in shuffled.events],
                         [e['id'] for e in self.timeline.events])
        self.assertEqual(shuffled.manifest['corpus_sha256'],
                         self.timeline.manifest['corpus_sha256'])


class DedupAndSkewTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Ingestor().ingest_corpus()

    def test_no_event_id_survives_twice(self):
        ids = [event['id'] for event in self.timeline.events]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 141)

    def test_synchronized_forwarder_duplicates_collapse_exactly(self):
        totals = self.timeline.manifest['totals']
        self.assertEqual(totals['duplicates_collapsed'], 2)
        b01 = self.timeline.of_scenario(B01)
        mirrored = [event for event in b01 if event['mirrored_in']]
        self.assertEqual(len(mirrored), 2)
        self.assertTrue(all(event['clock_skew_seconds'] == 0
                            for event in mirrored))

    def test_skewed_forwarder_duplicates_collapse_and_are_surfaced(self):
        totals = self.timeline.manifest['totals']
        self.assertEqual(totals['clock_skew_duplicates'], 18)
        self.assertEqual(totals['max_observed_clock_skew_seconds'], 7.0)
        skew = [entry for entry in self.timeline.uncertainty
                if entry['kind'] == 'clock_skew']
        self.assertEqual(len(skew), 1)
        self.assertEqual(skew[0]['max_observed_seconds'], 7.0)

    def test_authoritative_source_wins_the_skew(self):
        event = self.timeline.get('m01-000002')
        self.assertEqual(event['source_format'], 'json-audit')
        self.assertEqual(event['raw_ts'], '2026-01-04T09:00:00+00:00')
        self.assertEqual(event['tz_offset_minutes'], 0)
        self.assertEqual(len(event['mirrored_in']), 1)
        mirror = event['mirrored_in'][0]
        self.assertEqual(mirror['tz_offset_minutes'], 540)
        self.assertEqual(mirror['clock_skew_seconds'], 7.0)
        self.assertEqual(len(mirror['source_sha256']), 64)

    def test_same_id_with_different_content_raises(self):
        with self.assertRaises(ConflictingEventError) as caught:
            Ingestor().ingest(
                [ROOT / 'adversarial' / 'conflicting-same-id.jsonl'])
        self.assertIn('conflicting content', str(caught.exception))
        self.assertIn('ip', str(caught.exception))
        self.assertIn('user', str(caught.exception))

    def test_same_id_skewed_beyond_tolerance_raises(self):
        with self.assertRaises(ConflictingEventError) as caught:
            Ingestor().ingest(
                [ROOT / 'adversarial' / 'skew-beyond-tolerance.jsonl'])
        self.assertIn('600s', str(caught.exception))
        self.assertIn('beyond the 30s clock-skew tolerance',
                      str(caught.exception))

    def test_tolerance_is_configurable_not_hardcoded(self):
        wide = Ingestor(clock_skew_tolerance_seconds=900).ingest(
            [ROOT / 'adversarial' / 'skew-beyond-tolerance.jsonl'])
        self.assertEqual(len(wide.events), 1)
        self.assertEqual(wide.events[0]['clock_skew_seconds'], 600.0)
        with self.assertRaises(ValueError):
            Ingestor(clock_skew_tolerance_seconds=-1)


class MissingRecordTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Ingestor().ingest_corpus()

    def test_seq_holes_are_reported_with_their_numbers(self):
        missing = [entry for entry in self.timeline.uncertainty
                   if entry['kind'] == 'missing_records']
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['scenario'], M01)
        self.assertEqual(missing[0]['missing_seq'], [27, 28])
        self.assertEqual(missing[0]['count'], 2)
        self.assertEqual(self.timeline.manifest['totals']['missing_records'], 2)

    def test_absent_events_are_never_reconstructed(self):
        absent = scenarios.absent_event_ids(M01)
        self.assertEqual(absent, ['m01-000027', 'm01-000028'])
        for event_id in absent:
            self.assertFalse(self.timeline.has(event_id))
            self.assertIsNone(self.timeline.get(event_id))

    def test_rejected_line_leaves_a_visible_seq_hole(self):
        mixed = Ingestor().ingest(
            [ROOT / 'adversarial' / 'mixed-naive-and-offset.jsonl'])
        self.assertEqual([event['id'] for event in mixed.events],
                         ['adv-mixed-000001', 'adv-mixed-000003'])
        self.assertEqual([entry['kind'] for entry in mixed.uncertainty],
                         ['missing_records', 'rejected_lines', 'standing'])
        self.assertEqual(mixed.uncertainty[0]['missing_seq'], [2])

    def test_nothing_is_silently_dropped(self):
        totals = self.timeline.manifest['totals']
        parsed = sum(row['events_parsed']
                     for row in self.timeline.manifest['files'])
        self.assertEqual(totals['events'] + totals['duplicates_collapsed']
                         + totals['clock_skew_duplicates'], parsed)
        self.assertEqual(totals['lines_rejected'], len(self.timeline.rejected))


class TimezoneRejectionTests(unittest.TestCase):
    def test_a_source_with_no_offset_anywhere_is_refused_loudly(self):
        with self.assertRaises(NaiveTimestampError) as caught:
            Ingestor().ingest([ROOT / 'adversarial' / 'legacy-naive.log'])
        self.assertIn('refusing to guess a timezone', str(caught.exception))

    def test_one_bad_line_does_not_kill_a_otherwise_good_source(self):
        mixed = Ingestor().ingest(
            [ROOT / 'adversarial' / 'mixed-naive-and-offset.jsonl'])
        self.assertEqual(len(mixed.events), 2)
        self.assertEqual(len(mixed.rejected), 1)
        self.assertEqual(mixed.rejected[0]['reason'], 'naive_timestamp')
        self.assertEqual(mixed.rejected[0]['line_no'], 2)
        self.assertIn('raw', mixed.rejected[0])
        ledger = [entry for entry in mixed.uncertainty
                  if entry['kind'] == 'rejected_lines']
        self.assertEqual(ledger[0]['by_reason'], {'naive_timestamp': 1})

    def test_declared_offset_is_recorded_as_an_assumption(self):
        timeline = Ingestor().ingest(
            [ROOT / 'adversarial' / 'legacy-declared-offset.log'],
            declared_offsets={'legacy-declared-offset.log': -300})
        self.assertEqual(len(timeline.events), 2)
        self.assertTrue(all(event['tz_assumed'] for event in timeline.events))
        self.assertEqual({event['tz_offset_minutes']
                          for event in timeline.events}, {-300})
        entry = [item for item in timeline.uncertainty
                 if item['kind'] == 'timezone_assumption'][0]
        self.assertEqual(entry['event_count'], 2)
        self.assertEqual(entry['offsets_minutes'], [-300])
        self.assertEqual(
            timeline.manifest['files'][0]['timezone_assumption_recorded'],
            True)

    def test_mixed_offsets_are_normalized_consistently(self):
        mixed = Ingestor().ingest(
            [ROOT / 'adversarial' / 'mixed-naive-and-offset.jsonl'])
        self.assertEqual([event['tz_offset_minutes']
                          for event in mixed.events], [0, 540])
        self.assertEqual([event['at'] for event in mixed.events],
                         ['2026-01-04T09:00:00+00:00',
                          '2026-01-04T09:10:00+00:00'])


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Ingestor().ingest_corpus()

    def test_timeline_is_chronologically_ordered(self):
        epochs = [event['at_epoch'] for event in self.timeline.events]
        self.assertEqual(epochs, sorted(epochs))

    def test_cross_source_neighbours_are_marked_order_uncertain(self):
        flagged = [event for event in self.timeline.events
                   if event['order_uncertain']]
        self.assertEqual(len(flagged), 4)
        self.assertEqual({event['scenario'] for event in flagged}, {M01})
        self.assertEqual(
            [event['id'] for event in flagged],
            ['m01-000001', 'm01-000002', 'm01-000031', 'm01-000029'])
        for event in flagged:
            neighbours = [other for other in flagged
                          if other['source_file'] != event['source_file']]
            self.assertTrue(neighbours)
        ledger = [entry for entry in self.timeline.uncertainty
                  if entry['kind'] == 'clock_order_uncertain'][0]
        self.assertEqual(ledger['event_count'], 4)

    def test_uncertainty_ledger_is_structured_and_non_empty(self):
        kinds = {entry['kind'] for entry in self.timeline.uncertainty}
        self.assertEqual(kinds, {'clock_order_uncertain', 'clock_skew',
                                 'cross_source_duplicate', 'missing_records',
                                 'standing'})
        for entry in self.timeline.uncertainty:
            self.assertTrue(entry['detail'])
            self.assertEqual(entry['kind'], entry['kind'].strip())

    def test_provenance_lookup_round_trips_to_the_source_bytes(self):
        provenance = self.timeline.provenance('m01-000002')
        path = Path(provenance['source_file'])
        line = path.read_text(encoding='utf-8').splitlines()[
            provenance['source_line'] - 1]
        self.assertIn('m01-000002', line)
        self.assertEqual(provenance['source_sha256'], sha256_file(path))
        self.assertEqual(provenance['tz_offset_minutes'], 0)
        self.assertEqual(len(provenance['mirrored_in']), 1)

    def test_events_carry_no_ground_truth_label(self):
        forbidden = {'malicious', 'label', 'truth', 'attack', 'benign',
                     'ground_truth', 'y'}
        for event in self.timeline.events:
            self.assertFalse(forbidden & set(event))


class ReferenceKernelTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Ingestor().ingest_corpus()

    def test_projection_matches_the_reference_contract_exactly(self):
        projected = to_reference_events(self.timeline.events)
        self.assertTrue(projected)
        for event in projected:
            self.assertEqual(set(event), {'id', 'at', 'user', 'ip', 'kind'})
            self.assertIn(event['kind'], ('failure', 'success'))
        result = analyze(projected)
        self.assertEqual(len(result['input_sha256']), 64)

    def test_data_plane_events_are_excluded_and_counted(self):
        total = len(self.timeline.events)
        projected = to_reference_events(self.timeline.events)
        actions = sum(1 for event in self.timeline.events
                      if event['kind'] == 'action')
        self.assertEqual(len(projected), total - actions)
        self.assertGreater(actions, 0)

    def test_reference_kernel_runs_over_the_whole_corpus(self):
        result = analyze(to_reference_events(self.timeline.events))
        flagged = {finding['user'] for finding in result['findings']}
        self.assertEqual(flagged, {'u-1042', 'u-3311', 'u-5510', 'u-7731',
                                   'svc-helpdesk'})
        self.assertEqual(len(result['findings']), 5)
        for finding in result['findings']:
            self.assertEqual(finding['rule'], 'failures_then_success')
            for event_id in finding['evidence_ids']:
                self.assertTrue(self.timeline.has(event_id))


if __name__ == '__main__':
    unittest.main()
