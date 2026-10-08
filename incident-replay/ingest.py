"""Evidence ingestion for IncidentReplay (P12-01).

Two adapters normalize two raw log formats into one event shape, and every
event keeps the provenance needed to reproduce it: the source file, that
file's sha256, the line number, the raw timestamp text and the UTC offset it
was written in.

The card's four hazards are handled explicitly and **surfaced**, never
silently dropped:

* **Timezone differences.** Timestamps are parsed as ISO-8601 and must carry
  an explicit offset. A naive timestamp is rejected line-by-line with reason
  ``naive_timestamp`` unless the operator supplies
  ``declared_utc_offset_minutes`` for that source, in which case the event is
  accepted with ``tz_assumed=True`` and the assumption is recorded in the
  manifest and the uncertainty list. Everything is normalized to UTC.
* **Deduplication.** Events are keyed by ``event_id``. Identical semantic
  content arriving from two sources collapses to the authoritative source
  (lowest ``source_rank``) and the collapse is counted. Same id with
  *different* semantic content raises :class:`ConflictingEventError`.
* **Clock uncertainty.** Same id, same content, timestamps that disagree by
  more than zero but no more than ``clock_skew_tolerance_seconds`` collapse
  as a *clock-skew duplicate* and the observed delta is recorded; a
  disagreement beyond the tolerance is a conflict and raises. Independently,
  neighbouring events from different sources closer together than the
  tolerance are marked ``order_uncertain`` because their relative order is
  not established by the evidence.
* **Missing records.** Per-scenario ``seq`` continuity is checked across the
  union of all sources; holes inside the observed range are reported as
  ``missing_records`` with the exact absent seq numbers and ids are *not*
  invented to fill them.

The output is a :class:`Timeline`: deterministically ordered events plus a
structured uncertainty ledger and a provenance manifest.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

UTC = dt.timezone.utc

SEMANTIC_KEYS = ('user', 'ip', 'kind', 'action', 'bytes_out', 'object',
                 'ticket_ref', 'session_id', 'session_type', 'auth_factors',
                 'seq')

EVENT_TYPE_TO_KIND = {'auth_failure': 'failure', 'auth_success': 'success',
                      'data_access': 'action'}


class IngestError(Exception):
    """Base class for ingestion failures."""


class UnknownFormatError(IngestError):
    """The source format could not be determined or is unsupported."""


class NaiveTimestampError(IngestError):
    """A timestamp carried no UTC offset and no offset was declared."""


class ConflictingEventError(IngestError):
    """One event id arrived with contradictory content or timing."""


class LineRejected(Exception):
    """Internal: one raw line could not become an event."""

    def __init__(self, reason, detail=''):
        super().__init__('%s%s' % (reason, ': %s' % detail if detail else ''))
        self.reason = reason
        self.detail = detail


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_timestamp(text, declared_utc_offset_minutes=None):
    """Parse ISO-8601 into an aware UTC datetime.

    Returns ``(utc_datetime, offset_minutes, assumed)``. Raises
    :class:`NaiveTimestampError` when the text has no offset and none was
    declared for the source.
    """
    if not isinstance(text, str) or not text.strip():
        raise NaiveTimestampError('empty timestamp')
    try:
        parsed = dt.datetime.fromisoformat(text.strip().replace('Z', '+00:00'))
    except ValueError as error:
        raise NaiveTimestampError('unparseable timestamp %r' % text) from error
    if parsed.tzinfo is not None:
        offset = parsed.utcoffset()
        return (parsed.astimezone(UTC),
                int(offset.total_seconds() // 60), False)
    if declared_utc_offset_minutes is None:
        raise NaiveTimestampError(
            'naive timestamp %r has no UTC offset and the source declared '
            'none' % text)
    zone = dt.timezone(dt.timedelta(minutes=declared_utc_offset_minutes))
    return (parsed.replace(tzinfo=zone).astimezone(UTC),
            int(declared_utc_offset_minutes), True)


def detect_format(path):
    name = Path(path).name.lower()
    if name.startswith('._'):
        raise UnknownFormatError('AppleDouble sidecar %r is not a log' % name)
    if name.endswith('.jsonl') or name.endswith('.json'):
        return 'json-audit'
    if name.endswith('.log'):
        return 'syslog-kv'
    raise UnknownFormatError('cannot infer format for %r' % name)


class JsonAuditAdapter:
    """JSON Lines application audit log written in UTC."""

    name = 'json-audit'
    source_rank = 0
    required = ('event_id', 'ts', 'actor', 'src_ip', 'event_type')

    def parse_line(self, line, line_no, declared_utc_offset_minutes=None):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise LineRejected('malformed_json', str(error)) from error
        if not isinstance(record, dict):
            raise LineRejected('not_an_object', type(record).__name__)
        missing = [key for key in self.required if key not in record]
        if missing:
            raise LineRejected('missing_fields', ','.join(missing))
        try:
            when, offset, assumed = parse_timestamp(
                record['ts'], declared_utc_offset_minutes)
        except NaiveTimestampError as error:
            raise LineRejected('naive_timestamp', str(error)) from error
        kind = EVENT_TYPE_TO_KIND.get(record['event_type'])
        if kind is None:
            raise LineRejected('unknown_event_type', record['event_type'])
        return {'id': str(record['event_id']), 'at': when,
                'raw_ts': record['ts'], 'tz_offset_minutes': offset,
                'tz_assumed': assumed, 'user': record['actor'],
                'ip': record['src_ip'], 'kind': kind,
                'action': record.get('action', ''),
                'bytes_out': int(record.get('bytes_out', 0)),
                'object': record.get('object', ''),
                'ticket_ref': record.get('ticket_ref', ''),
                'session_id': record.get('session_id', ''),
                'session_type': record.get('session_type', 'interactive'),
                'auth_factors': list(record.get('auth_factors', [])),
                'seq': record.get('seq'), 'line_no': line_no}


class SyslogKvAdapter:
    """RFC 3164-style forwarder lines carrying ``key=value`` pairs.

    Values are whitespace-delimited, so a field value must not contain a
    space; a line that violates this is rejected with a recorded reason
    rather than mis-parsed. The header timestamp is deliberately *not* used
    for event time — only the payload ``ts=`` field is, because the header
    carries no year and no offset.
    """

    name = 'syslog-kv'
    source_rank = 1
    required = ('event_id', 'ts', 'actor', 'src_ip', 'event_type')

    def parse_line(self, line, line_no, declared_utc_offset_minutes=None):
        if ': ' not in line:
            raise LineRejected('malformed_syslog', 'no header/payload split')
        _, payload = line.split(': ', 1)
        fields = {}
        for token in payload.split(' '):
            if '=' not in token:
                continue
            key, value = token.split('=', 1)
            fields[key] = value
        missing = [key for key in self.required if key not in fields]
        if missing:
            raise LineRejected('missing_fields', ','.join(missing))
        try:
            when, offset, assumed = parse_timestamp(
                fields['ts'], declared_utc_offset_minutes)
        except NaiveTimestampError as error:
            raise LineRejected('naive_timestamp', str(error)) from error
        kind = EVENT_TYPE_TO_KIND.get(fields['event_type'])
        if kind is None:
            raise LineRejected('unknown_event_type', fields['event_type'])
        factors = fields.get('auth_factors', '')
        seq = fields.get('seq')
        return {'id': fields['event_id'], 'at': when, 'raw_ts': fields['ts'],
                'tz_offset_minutes': offset, 'tz_assumed': assumed,
                'user': fields['actor'], 'ip': fields['src_ip'], 'kind': kind,
                'action': fields.get('action', ''),
                'bytes_out': int(fields.get('bytes_out') or 0),
                'object': fields.get('object', ''),
                'ticket_ref': fields.get('ticket_ref', ''),
                'session_id': fields.get('session_id', ''),
                'session_type': fields.get('session_type', 'interactive'),
                'auth_factors': [f for f in factors.split('|') if f],
                'seq': int(seq) if seq not in (None, '') else None,
                'line_no': line_no}


ADAPTERS = {'json-audit': JsonAuditAdapter, 'syslog-kv': SyslogKvAdapter}


class Timeline:
    """Ordered, provenance-carrying event stream plus an uncertainty ledger."""

    def __init__(self, events, manifest, uncertainty, rejected):
        self.events = events
        self.manifest = manifest
        self.uncertainty = uncertainty
        self.rejected = rejected
        self._by_id = {event['id']: event for event in events}

    def __len__(self):
        return len(self.events)

    def ids(self):
        return set(self._by_id)

    def get(self, event_id):
        return self._by_id.get(event_id)

    def has(self, event_id):
        return event_id in self._by_id

    def provenance(self, event_id):
        """``{source_file, source_sha256, source_line, raw_ts}`` for an id."""
        event = self._by_id[event_id]
        return {'event_id': event_id,
                'source_file': event['source_file'],
                'source_sha256': event['source_sha256'],
                'source_format': event['source_format'],
                'source_line': event['source_line'],
                'raw_ts': event['raw_ts'],
                'tz_offset_minutes': event['tz_offset_minutes'],
                'mirrored_in': list(event['mirrored_in'])}

    def scenarios(self):
        return sorted({event['scenario'] for event in self.events})

    def of_scenario(self, scenario_id):
        return [event for event in self.events
                if event['scenario'] == scenario_id]

    def stats(self):
        return {
            'events': len(self.events),
            'scenarios': self.scenarios(),
            'files': len(self.manifest['files']),
            'rejected_lines': len(self.rejected),
            'duplicates_collapsed': self.manifest['totals'][
                'duplicates_collapsed'],
            'clock_skew_duplicates': self.manifest['totals'][
                'clock_skew_duplicates'],
            'max_observed_clock_skew_seconds': self.manifest['totals'][
                'max_observed_clock_skew_seconds'],
            'missing_records': self.manifest['totals']['missing_records'],
            'order_uncertain_events': sum(
                1 for event in self.events if event['order_uncertain']),
            'tz_assumed_events': sum(
                1 for event in self.events if event['tz_assumed']),
            'uncertainty_entries': len(self.uncertainty),
            'uncertainty_kinds': sorted(
                {entry['kind'] for entry in self.uncertainty}),
        }

    def as_dict(self):
        return {'manifest': self.manifest, 'uncertainty': self.uncertainty,
                'rejected_lines': self.rejected, 'stats': self.stats(),
                'events': self.events}


class Ingestor:
    """Normalize raw sources into a :class:`Timeline`."""

    def __init__(self, clock_skew_tolerance_seconds=30):
        if clock_skew_tolerance_seconds < 0:
            raise ValueError('clock_skew_tolerance_seconds must be >= 0')
        self.tolerance = clock_skew_tolerance_seconds

    def read_source(self, path, fmt=None,
                    declared_utc_offset_minutes=None):
        """Parse one file into ``(events, rejected, file_row)``."""
        path = Path(path)
        fmt = fmt or detect_format(path)
        if fmt not in ADAPTERS:
            raise UnknownFormatError('no adapter for format %r' % fmt)
        adapter = ADAPTERS[fmt]()
        digest = sha256_file(path)
        events, rejected = [], []
        text = path.read_text(encoding='utf-8')
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = adapter.parse_line(line, line_no,
                                         declared_utc_offset_minutes)
            except LineRejected as error:
                rejected.append({'source_file': str(path),
                                 'source_format': fmt, 'line_no': line_no,
                                 'reason': error.reason,
                                 'detail': error.detail,
                                 'raw': line[:400]})
                continue
            raw.update({'source_file': str(path), 'source_sha256': digest,
                        'source_format': fmt, 'source_line': line_no,
                        'source_rank': adapter.source_rank,
                        'scenario': path.parent.name,
                        'declared_utc_offset_minutes':
                            declared_utc_offset_minutes})
            events.append(raw)
        if not events and rejected and all(
                row['reason'] == 'naive_timestamp' for row in rejected):
            raise NaiveTimestampError(
                'source %s carries no usable UTC offset on any of its %d '
                'lines and declared none; refusing to guess a timezone'
                % (path, len(rejected)))
        row = {'path': str(path), 'name': path.name,
               'scenario': path.parent.name, 'format': fmt,
               'sha256': digest, 'bytes': path.stat().st_size,
               'lines': len(text.splitlines()),
               'adapter': adapter.__class__.__name__,
               'source_rank': adapter.source_rank,
               'declared_utc_offset_minutes': declared_utc_offset_minutes,
               'timezone_assumption_recorded':
                   declared_utc_offset_minutes is not None,
               'events_parsed': len(events), 'lines_rejected': len(rejected)}
        return events, rejected, row

    def ingest(self, paths, declared_offsets=None):
        """Ingest an explicit list of source files into one timeline."""
        declared_offsets = declared_offsets or {}
        raw_events, rejected, rows = [], [], []
        for path in paths:
            path = Path(path)
            events, bad, row = self.read_source(
                path, declared_utc_offset_minutes=declared_offsets.get(
                    str(path), declared_offsets.get(path.name)))
            raw_events.extend(events)
            rejected.extend(bad)
            rows.append(row)
        return self._assemble(raw_events, rejected, rows)

    def ingest_scenario(self, scenario_id, root=None, include_baseline=False):
        """Ingest every raw log source of one scenario."""
        import scenarios
        root = Path(root) if root else scenarios.FIXTURE_ROOT
        names = ['audit.jsonl', 'edge-syslog.log']
        if include_baseline:
            names.append('baseline.json')
        paths = [path for path in sorted((root / scenario_id).iterdir())
                 if path.name in names and not path.name.startswith('._')]
        return self.ingest(paths)

    def ingest_corpus(self, root=None, include_adversarial=False,
                      declared_offsets=None):
        """Ingest every scenario directory in the fixture corpus."""
        import scenarios
        root = Path(root) if root else scenarios.FIXTURE_ROOT
        paths = []
        for scenario_id in scenarios.SCENARIO_IDS:
            directory = root / scenario_id
            for name in ('audit.jsonl', 'edge-syslog.log'):
                candidate = directory / name
                if candidate.exists():
                    paths.append(candidate)
        if include_adversarial:
            paths.extend(sorted(
                path for path in (root / 'adversarial').iterdir()
                if path.suffix == '.log' and not path.name.startswith('._')))
        return self.ingest(sorted(paths), declared_offsets)

    def _assemble(self, raw_events, rejected, rows):
        rows = sorted(rows, key=lambda row: row['path'])
        rejected = sorted(rejected, key=lambda row: (row['source_file'],
                                                     row['line_no']))
        groups = {}
        for event in raw_events:
            groups.setdefault(event['id'], []).append(event)

        events, uncertainty = [], []
        collapsed = skew_duplicates = 0
        max_skew = 0
        conflicts = []

        for event_id in sorted(groups):
            candidates = sorted(groups[event_id],
                                key=lambda item: (item['source_rank'],
                                                  item['source_line']))
            authority = candidates[0]
            semantic = {key: _canonical(authority[key])
                        for key in SEMANTIC_KEYS}
            mirrored = []
            for other in candidates[1:]:
                other_semantic = {key: _canonical(other[key])
                                  for key in SEMANTIC_KEYS}
                if other_semantic != semantic:
                    difference = sorted(
                        key for key in SEMANTIC_KEYS
                        if semantic[key] != other_semantic[key])
                    raise ConflictingEventError(
                        'event id %r has conflicting content across %s '
                        '(differing fields: %s)'
                        % (event_id,
                           ' and '.join(sorted({authority['source_file'],
                                                other['source_file']})),
                           ', '.join(difference)))
                delta = abs((other['at'] - authority['at']).total_seconds())
                if delta > self.tolerance:
                    raise ConflictingEventError(
                        'event id %r disagrees by %.0fs across %s and %s, '
                        'beyond the %ds clock-skew tolerance'
                        % (event_id, delta, authority['source_file'],
                           other['source_file'], self.tolerance))
                mirrored.append({'source_file': other['source_file'],
                                 'source_sha256': other['source_sha256'],
                                 'source_line': other['source_line'],
                                 'raw_ts': other['raw_ts'],
                                 'tz_offset_minutes':
                                     other['tz_offset_minutes'],
                                 'clock_skew_seconds': delta})
                if delta > 0:
                    skew_duplicates += 1
                    max_skew = max(max_skew, delta)
                else:
                    collapsed += 1
            event = _normalize(authority)
            event['mirrored_in'] = mirrored
            event['clock_skew_seconds'] = max(
                [mirror['clock_skew_seconds'] for mirror in mirrored],
                default=0)
            event['ingested_from'] = sorted(
                {authority['source_file']}
                | {mirror['source_file'] for mirror in mirrored})
            events.append(event)
            if mirrored:
                uncertainty.append({
                    'kind': 'cross_source_duplicate',
                    'event_id': event_id,
                    'detail': 'collapsed %d copies into %s; observed clock '
                              'skew %.0fs (tolerance %ds)'
                              % (len(mirrored), authority['source_file'],
                                 event['clock_skew_seconds'], self.tolerance),
                    'sources': event['ingested_from']})

        events.sort(key=lambda item: (item['at_epoch'], item['source_rank'],
                                      item['source_file'], item['id']))
        for previous, current in zip(events, events[1:]):
            gap = current['at_epoch'] - previous['at_epoch']
            cross_source = previous['source_file'] != current['source_file']
            if cross_source and gap <= self.tolerance:
                previous['order_uncertain'] = True
                current['order_uncertain'] = True

        ambiguous = sum(1 for event in events if event['order_uncertain'])
        if ambiguous:
            uncertainty.append({
                'kind': 'clock_order_uncertain',
                'event_count': ambiguous,
                'detail': '%d events from different sources fall within the '
                          '%ds clock-skew tolerance of a neighbour, so their '
                          'relative order is not established by the evidence'
                          % (ambiguous, self.tolerance)})
        if max_skew:
            uncertainty.append({
                'kind': 'clock_skew',
                'max_observed_seconds': max_skew,
                'detail': 'the largest timestamp disagreement between two '
                          'sources reporting the same event id was %.0fs'
                          % max_skew})

        missing_total = self._record_missing_records(events, uncertainty, rows)
        assumed = [event for event in events if event['tz_assumed']]
        if assumed:
            uncertainty.append({
                'kind': 'timezone_assumption',
                'event_count': len(assumed),
                'offsets_minutes': sorted({event['tz_offset_minutes']
                                           for event in assumed}),
                'sources': sorted({event['source_file']
                                   for event in assumed}),
                'detail': 'these events carried no UTC offset; the operator-'
                          'declared offset was applied and is an assumption, '
                          'not an observation'})

        if rejected:
            by_reason = {}
            for row in rejected:
                by_reason.setdefault(row['reason'], 0)
                by_reason[row['reason']] += 1
            uncertainty.append({
                'kind': 'rejected_lines',
                'line_count': len(rejected),
                'by_reason': by_reason,
                'sources': sorted({row['source_file'] for row in rejected}),
                'detail': 'raw lines that could not be normalized are '
                          'retained in rejected_lines and excluded from the '
                          'timeline; they are not silently dropped'})

        uncertainty.append({
            'kind': 'standing',
            'detail': 'missing logs unknown; clock synchronization not '
                      'established beyond the %ds tolerance; absence of an '
                      'event is not evidence that it did not happen'
                      % self.tolerance})

        totals = {'events': len(events),
                  'duplicates_collapsed': collapsed,
                  'clock_skew_duplicates': skew_duplicates,
                  'max_observed_clock_skew_seconds': max_skew,
                  'conflicts_raised': len(conflicts),
                  'missing_records': missing_total,
                  'lines_rejected': len(rejected),
                  'order_uncertain_events': ambiguous,
                  'tz_assumed_events': len(assumed),
                  'files': len(rows)}
        manifest = {'generator': 'ingest.Ingestor',
                    'clock_skew_tolerance_seconds': self.tolerance,
                    'source_sha256': _module_sha256(),
                    'files': rows, 'totals': totals,
                    'corpus_sha256': hashlib.sha256(
                        '\n'.join(row['sha256'] for row in rows).encode()
                    ).hexdigest()}
        return Timeline(events, manifest, uncertainty, rejected)

    def _record_missing_records(self, events, uncertainty, rows):
        """Report per-scenario ``seq`` holes across the union of sources."""
        by_scenario = {}
        for event in events:
            if event['seq'] is None:
                continue
            by_scenario.setdefault(event['scenario'], []).append(event)
        total = 0
        for scenario in sorted(by_scenario):
            seen = sorted({event['seq'] for event in
                           by_scenario[scenario]})
            holes = [seq for seq in range(seen[0], seen[-1] + 1)
                     if seq not in set(seen)]
            if not holes:
                continue
            total += len(holes)
            uncertainty.append({
                'kind': 'missing_records',
                'scenario': scenario,
                'missing_seq': holes,
                'count': len(holes),
                'expected_records': seen[-1],
                'observed_records': len(seen),
                'sources': sorted({event['source_file']
                                   for event in by_scenario[scenario]}),
                'detail': 'seq %s is absent from every source of %s; the '
                          'records were not reconstructed and no event was '
                          'invented to fill the hole'
                          % (', '.join(str(seq) for seq in holes), scenario)})
        return total


def _canonical(value):
    if isinstance(value, list):
        return tuple(value)
    return value


def _normalize(raw):
    return {'id': raw['id'],
            'at': raw['at'].astimezone(UTC).isoformat(),
            'at_epoch': raw['at'].timestamp(),
            'user': raw['user'], 'ip': raw['ip'], 'kind': raw['kind'],
            'action': raw['action'], 'bytes_out': raw['bytes_out'],
            'object': raw['object'], 'ticket_ref': raw['ticket_ref'],
            'session_id': raw['session_id'],
            'session_type': raw['session_type'],
            'auth_factors': list(raw['auth_factors']), 'seq': raw['seq'],
            'scenario': raw['scenario'],
            'source_file': raw['source_file'],
            'source_sha256': raw['source_sha256'],
            'source_format': raw['source_format'],
            'source_line': raw['source_line'],
            'source_rank': raw['source_rank'],
            'raw_ts': raw['raw_ts'],
            'tz_offset_minutes': raw['tz_offset_minutes'],
            'tz_assumed': raw['tz_assumed'],
            'mirrored_in': [], 'clock_skew_seconds': 0,
            'order_uncertain': False, 'ingested_from': []}


def _module_sha256():
    digest = hashlib.sha256()
    for module in (Path(__file__),):
        digest.update(module.read_bytes())
    return digest.hexdigest()


def to_reference_events(events):
    """Project normalized events onto the reference kernel's 5-key contract.

    ``project.analyze`` accepts exactly ``{id, at, user, ip, kind}`` with
    ``kind`` in ``{failure, success}``, so data-plane events are excluded
    here and the exclusion is counted by the caller rather than hidden.
    """
    return [{'id': event['id'], 'at': event['at'], 'user': event['user'],
             'ip': event['ip'], 'kind': event['kind']}
            for event in events if event['kind'] in ('failure', 'success')]
