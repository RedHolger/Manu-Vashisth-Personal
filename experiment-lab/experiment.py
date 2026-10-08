"""Metric contract for ExperimentLab (P07-01): configuration, randomized
assignment, exposure logging with deduplication, and SQL extraction.

Everything here is deliberately boring and hand-checkable: the analysis in
`project.py` needs one outcome per randomized user inside a fixed horizon,
and this module is what guarantees those denominators. Assignment is a
stable hash (no RNG state to lose); the store is SQLite with PRIMARY KEYs so
a repeated exposure or outcome cannot silently double-count a user.
"""
import hashlib
import sqlite3

ALLOCATIONS = ('A', 'B')

# The supported YAML subset, documented so a config that parses is a config
# with unambiguous meaning: mappings via `key: value` (two-space indent for
# nesting), lists via `- item`, scalars as bare words, numbers, booleans or
# single/double-quoted strings. Tabs, flow collections and anchors are
# rejected rather than guessed at.
REQUIRED_KEYS = ('unit', 'hypothesis', 'primary_metric', 'allocation',
                 'horizon_days')


def parse_subset_yaml(text):
    """Parse the documented YAML subset into nested dicts/lists."""
    root = {}
    stack = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.strip().startswith('#'):
            continue
        if '\t' in raw:
            raise ValueError('line %d: tabs are not allowed' % lineno)
        indent = len(raw) - len(raw.lstrip(' '))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError('line %d: bad indentation' % lineno)
        _, parent = stack[-1]
        if line.startswith('- '):
            if not isinstance(parent, list):
                raise ValueError('line %d: list item outside a list' % lineno)
            parent.append(_scalar(line[2:].strip(), lineno))
            continue
        key, sep, value = line.partition(':')
        key, value = key.strip(), value.strip()
        if not sep or not key:
            raise ValueError('line %d: expected `key: value`' % lineno)
        if isinstance(parent, list):
            raise ValueError('line %d: mapping entry inside a list' % lineno)
        if key in parent:
            raise ValueError('line %d: duplicate key %r' % (lineno, key))
        if value == '':
            child = [] if _peek_is_list(text.splitlines(), lineno) else {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value, lineno)
    return root


def _peek_is_list(lines, lineno):
    for raw in lines[lineno:]:
        if not raw.strip() or raw.strip().startswith('#'):
            continue
        return raw.strip().startswith('- ')
    return False


def _scalar(value, lineno):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    low = value.lower()
    if low in ('true', 'false'):
        return low == 'true'
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if any(token in value for token in ('{', '}', '[', ']', '&', '*', '|',
                                        '>', '!')):
        raise ValueError('line %d: flow syntax is not supported' % lineno)
    return value


def load_config(text):
    """Validate an experiment configuration; raise ValueError if it lies."""
    config = parse_subset_yaml(text)
    for key in REQUIRED_KEYS:
        if key not in config:
            raise ValueError('missing required key %r' % key)
    allocation = config['allocation']
    if (not isinstance(allocation, dict)
            or set(allocation) != set(ALLOCATIONS)
            or any(not isinstance(weight, (int, float)) or weight < 0
                   for weight in allocation.values())
            or sum(allocation.values()) <= 0):
        raise ValueError('allocation must map A and B to non-negative '
                         'weights with a positive total')
    horizon = config['horizon_days']
    if not isinstance(horizon, int) or isinstance(horizon, bool) \
            or horizon < 1:
        raise ValueError('horizon_days must be a positive integer')
    seed = config.get('randomization_seed', 7)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError('randomization_seed must be an integer')
    return config


def assign_arm(unit_id, allocation, seed=7):
    """Deterministic arm from sha256(seed, unit_id); no RNG state involved."""
    total = sum(allocation.values())
    digest = hashlib.sha256(('%d\x00%s' % (seed, unit_id)).encode()).hexdigest()
    point = int(digest, 16) / 16 ** 64
    if point < allocation['A'] / total:
        return 'A'
    return 'B'


SCHEMA = """
CREATE TABLE IF NOT EXISTS exposures (
  unit_id TEXT PRIMARY KEY,
  arm TEXT NOT NULL CHECK (arm IN ('A', 'B')),
  exposed_at TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS outcomes (
  unit_id TEXT PRIMARY KEY,
  outcome REAL NOT NULL,
  observed_at TEXT NOT NULL
);
"""


def connect(path=':memory:'):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def log_exposure(conn, unit_id, arm, exposed_at, source=''):
    """First exposure wins: a re-exposed unit keeps its original arm, and the
    caller is told whether this call was the one that counted."""
    if arm not in ALLOCATIONS:
        raise ValueError('unknown arm %r' % arm)
    cursor = conn.execute(
        'INSERT OR IGNORE INTO exposures (unit_id, arm, exposed_at, source) '
        'VALUES (?, ?, ?, ?)', (unit_id, arm, exposed_at, source))
    conn.commit()
    return cursor.rowcount == 1


def record_outcome(conn, unit_id, outcome, observed_at):
    """First outcome wins; repeats are ignored and reported as duplicates."""
    if not isinstance(outcome, (int, float)):
        raise ValueError('outcome must be numeric')
    cursor = conn.execute(
        'INSERT OR IGNORE INTO outcomes (unit_id, outcome, observed_at) '
        'VALUES (?, ?, ?)', (unit_id, float(outcome), observed_at))
    conn.commit()
    return cursor.rowcount == 1


def extract_analysis_rows(conn, horizon_end):
    """SQL extraction: one row per exposed user with an in-horizon outcome.

    Late outcomes (observed after the fixed horizon) are excluded, never
    trimmed; units without any outcome never reach the analysis. The
    denominator report counts everything the SQL saw so a reviewer can
    reconcile every user.
    """
    exposed = conn.execute('SELECT COUNT(*) FROM exposures').fetchone()[0]
    rows = conn.execute(
        'SELECT e.unit_id, e.arm, o.outcome '
        'FROM exposures e JOIN outcomes o ON o.unit_id = e.unit_id '
        'WHERE o.observed_at <= ? '
        'ORDER BY e.unit_id', (horizon_end,)).fetchall()
    late = conn.execute(
        'SELECT COUNT(*) FROM outcomes o JOIN exposures e '
        'ON o.unit_id = e.unit_id WHERE o.observed_at > ?',
        (horizon_end,)).fetchone()[0]
    unexposed_outcomes = conn.execute(
        'SELECT COUNT(*) FROM outcomes o LEFT JOIN exposures e '
        'ON o.unit_id = e.unit_id WHERE e.unit_id IS NULL').fetchone()[0]
    missing_outcomes = conn.execute(
        'SELECT COUNT(*) FROM exposures e LEFT JOIN outcomes o '
        'ON o.unit_id = e.unit_id WHERE o.unit_id IS NULL').fetchone()[0]
    per_arm = {}
    for _, arm, _ in rows:
        per_arm[arm] = per_arm.get(arm, 0) + 1
    return {
        'rows': [{'user': unit, 'arm': arm, 'outcome': outcome}
                 for unit, arm, outcome in rows],
        'denominators': {
            'exposed_units': exposed,
            'analysis_rows': len(rows),
            'per_arm': per_arm,
            'excluded_late_outcomes': late,
            'outcomes_without_exposure': unexposed_outcomes,
            'exposed_without_outcome': missing_outcomes,
        },
    }
