"""Segmented cohort analysis for CohortLens (P08-02).

Splits the P08-01 cohort table by an explicit user segment plus an explicit
activation window, with per-user completeness gating for every denominator.

Rules (both Python and segments.sql implement these):
- Events use the v1 schema enforced by ingest.py (exact keys, UTC-only).
- Segments come from a separate user_id -> label mapping (user_segments
  table in SQLite). Users without a mapping fall into 'unknown', which is
  reported as its own row — never dropped and never counted as zero.
- Activation window is explicit: activate in [signup, signup+window).
  A user enters the activation denominator only when
  asof >= signup + window; otherwise activation_rate is None.
- Week-1 retention is unchanged from P08-01: active in [signup+7,
  signup+14), denominator only when asof >= signup+14.
- Cohort-age filtering is per-user eligibility, plus the mature_only()
  helper that keeps only fully-mature (eligible == users) rows for a
  complete-window view.
"""
import datetime as dt
from pathlib import Path

from ingest import parse_utc

UNKNOWN = 'unknown'
QUERY = Path(__file__).with_name('segments.sql').read_text(encoding='utf-8')


def _check_window(days):
    if not isinstance(days, int) or isinstance(days, bool):
        raise ValueError('activation_window_days must be an int, got %r'
                         % (days,))
    if not 1 <= days <= 30:
        raise ValueError('activation_window_days must be 1..30, got %r'
                         % (days,))
    return days


def normalize_segments(mapping):
    """Validate a user_id -> segment mapping; None means all unknown."""
    if mapping is None:
        return {}
    if not isinstance(mapping, dict):
        raise ValueError('segments must be a dict or None')
    clean = {}
    for user_id, segment in mapping.items():
        if not isinstance(user_id, str) or not user_id:
            raise ValueError('user_id must be a non-empty string')
        if not isinstance(segment, str) or not segment:
            raise ValueError('segment must be a non-empty string')
        clean[user_id] = segment
    return clean


def segment_cohorts(events, as_of, segments=None, activation_window_days=7):
    """Segmented cohorts keyed by (monday, segment) tuples."""
    window = _check_window(activation_window_days)
    segmap = normalize_segments(segments)
    cutoff = parse_utc(as_of)
    seen = {}
    users = {}
    for event in events:
        if set(event) != {'id', 'user', 'type', 'at', 'ingested_at'}:
            raise ValueError('invalid event schema')
        at = parse_utc(event['at'])
        ingested = parse_utc(event['ingested_at'])
        if ingested > cutoff or at > cutoff:
            continue
        if event['id'] in seen:
            old = seen[event['id']]
            if any(old[key] != event[key] for key in ('user', 'type', 'at')):
                raise ValueError('conflicting duplicate event')
            continue
        seen[event['id']] = event
        users.setdefault(event['user'], []).append((at, event['type']))
    groups = {}
    for user, items in users.items():
        signs = [moment for moment, kind in items if kind == 'signup']
        if not signs:
            continue
        signup = min(signs)
        monday = (signup - dt.timedelta(days=signup.weekday())).date(
            ).isoformat()
        label = segmap.get(user, UNKNOWN)
        key = (monday, label)
        group = groups.setdefault(key, {'users': 0, 'activated': 0,
                                        'activation_eligible': 0,
                                        'activation_rate': None,
                                        'week1_eligible': 0,
                                        'week1_retained': 0,
                                        'week1_retention': None})
        group['users'] += 1
        if cutoff >= signup + dt.timedelta(days=window):
            group['activation_eligible'] += 1
            if any(kind == 'activate' and signup <= moment
                   < signup + dt.timedelta(days=window)
                   for moment, kind in items):
                group['activated'] += 1
        if cutoff >= signup + dt.timedelta(days=14):
            group['week1_eligible'] += 1
            if any(kind == 'active' and signup + dt.timedelta(days=7)
                   <= moment < signup + dt.timedelta(days=14)
                   for moment, kind in items):
                group['week1_retained'] += 1
    for group in groups.values():
        if group['activation_eligible']:
            group['activation_rate'] = (group['activated']
                                       / group['activation_eligible'])
        if group['week1_eligible']:
            group['week1_retention'] = (group['week1_retained']
                                       / group['week1_eligible'])
    return {'as_of': cutoff.isoformat(),
            'activation_window_days': window,
            'definition': ('activate in [signup, signup+%dd); week1 active '
                           'in [signup+7d, signup+14d); only complete '
                           'windows in denominators; unmapped users are '
                           "'unknown'") % window,
            'cohorts': groups}


def mature_only(table, window='week1'):
    """Keep only fully-mature rows for a complete-window view.

    window='activation' keeps rows with activation_eligible == users;
    window='week1' keeps rows with week1_eligible == users. Empty input
    stays empty; partially-mature rows are dropped (not zeroed).
    """
    if window not in ('activation', 'week1'):
        raise ValueError("window must be 'activation' or 'week1'")
    field = 'activation_eligible' if window == 'activation' else \
        'week1_eligible'
    return {key: dict(group) for key, group in table.items()
            if group['users'] > 0 and group[field] == group['users']}


def to_jsonable(table):
    """Convert (monday, segment) keys to 'monday|segment' for JSON."""
    return {'%s|%s' % key: value for key, value in sorted(table.items())}


def sql_segment_cohorts(conn, as_of, activation_window_days=7):
    """Segmented cohorts from SQL; same shape as segment_cohorts()."""
    window = _check_window(activation_window_days)
    cutoff = parse_utc(as_of).isoformat()
    groups = {}
    rows = conn.execute(QUERY, {'asof': cutoff,
                               'act_days': window}).fetchall()
    for (monday, segment, users, activated, act_eligible, eligible,
         retained, act_rate, retention) in rows:
        groups[(monday, segment)] = {'users': users, 'activated': activated,
                                     'activation_eligible': act_eligible,
                                     'activation_rate': act_rate,
                                     'week1_eligible': eligible,
                                     'week1_retained': retained,
                                     'week1_retention': retention}
    return groups
