"""Protocol validation and tooling pilot for UserEvidence (P15-01).

Validates that `PROTOCOL.md` defines two distinct studies with neutral tasks
(banned leading phrasing is scanned in the TASK text, not the meta-discussion
that names the banned list), that `CONSENT_FORM.md` carries the required
guarantees, and that the record pipeline runs end-to-end on synthetic
fixtures (`pilot_tooling()`). A human pilot needs consenting participants and
is BLOCKED; the tooling pilot proves the shape, not the findings.
"""
from pathlib import Path

import project

BANNED_PHRASES = ['you should', 'obviously', 'clearly shows',
                  'as you can see', 'just click', 'simply']
PROTOCOL_REQUIRED = ['## Study A', '## Study B', 'Neutral tasks',
                     'Banned phrasing', 'Pilot script', 'Ethics',
                     'Never fabricate']
CONSENT_REQUIRED = ['granted: true', 'Voluntary', 'stop at any time',
                    'deletion', 'pseudonym', 'No name']


def _normalized(text):
    """Collapse all whitespace so line wraps cannot hide a guarantee."""
    return ' '.join(text.split())


def validate_tasks(tasks):
    """Tasks must be non-empty strings free of leading phrasing."""
    if not tasks or not all(isinstance(t, str) and t.strip() for t in tasks):
        return False, 'tasks must be non-empty strings'
    lowered = [_normalized(t).lower() for t in tasks]
    for phrase in BANNED_PHRASES:
        if any(phrase in t for t in lowered):
            return False, 'leading phrase %r in a task' % phrase
    return True, 'ok'


def validate_protocol(text):
    text = _normalized(text)
    missing = [s for s in PROTOCOL_REQUIRED if s not in text]
    if missing:
        return False, 'missing sections: %s' % ', '.join(missing)
    if not all(p in text for p in BANNED_PHRASES):
        return False, 'banned list not declared'
    if 'BLOCKED' not in text or 'synthetic' not in text.lower():
        return False, 'must state blocked recruitment + synthetic fixtures'
    return True, 'ok'


def validate_consent(text):
    text = _normalized(text)
    missing = [s for s in CONSENT_REQUIRED if s not in text]
    if missing:
        return False, 'missing guarantees: %s' % ', '.join(missing)
    return True, 'ok'


def study_tasks():
    """The six neutral tasks (3 per study) the protocol actually assigns."""
    return [
        'Open the incident list. For incident INC-104, tell me what you see '
        'for its freshness.',
        'This export was loaded 40 minutes ago. Show me where you would '
        'check that.',
        'You need the source of the numbers on this chart. Walk me through '
        'how you would find it.',
        'Add a 90-minute study block for Thursday evening.',
        'This block overlaps a prerequisite. Tell me what the planner shows.',
        'Import this course file. Tell me what happened to your existing plan.',
    ]


def pilot_tooling():
    """End-to-end record-shape pilot on synthetic fixtures (no humans)."""
    rows = [{'participant': 'synthetic-%02d' % i, 'task': 'task-%d' % (i % 3),
             'success': bool(i % 2), 'seconds': 20 + i,
             'observation': 'Fixture observation %d' % i,
             'codes': ['visibility'] if i % 2 else [], 'synthetic': True}
            for i in range(6)]
    summary = project.summarize(rows)
    return {'rows': len(rows), 'synthetic_rows': summary['synthetic_rows'],
            'human_rows': len(rows) - summary['synthetic_rows'],
            'tasks_covered': sorted(summary['tasks']),
            'summary': summary}
