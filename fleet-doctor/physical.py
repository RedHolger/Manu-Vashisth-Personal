"""Physical-machine gate for FleetDoctor (P18-04): BLOCKED, labeled as such.

No supervised spare machine was made available, so NO hardware work was
performed. This module records that fact and guards it: `probe_spare()`
reports BLOCKED (there is nothing to probe — inventing a probe would be
theater), and `hardware_claim_scan()` flags affirmative server-repair claims
anywhere in the results, so process-level lab work can never be described as
hardware repair.
"""
HARDWARE_BANNED = ['server repair', 'hardware fixed', 'replaced the disk',
                   'repaired the server', 'fixed hardware', 'board repaired',
                   'physical repair complete']
NEGATIONS = ('no ', 'not ', 'never ', 'without ', 'refuse', 'blocked',
             "isn't", "aren't", 'neither ', 'nor ', 'forbids', 'against ')


def probe_spare():
    return {'status': 'BLOCKED', 'machine': None,
            'reason': 'no supervised spare machine was made available; no '
                      'hardware work performed, none claimed'}


def hardware_work_performed():
    return {'machines_touched': 0, 'repairs': [],
            'containers_used': False, 'vms_used': False,
            'lab_level': 'process-and-directory (owned temp resources only)',
            'statement': 'No hardware work was performed. Process-level lab '
                         'results must never be described as server repair.'}


def hardware_claim_scan(root='results'):
    """Affirmative hardware-repair claims; returns hits (must be empty).

    Negations are searched in an 80-char window around each phrase (not just
    its line), so a disclaimer wrapped across lines ('...forbids\\n
    describing ... server repair') still exempts. An affirmative claim with
    no nearby negation is flagged. (Codex fixes 2026-10-08: naive substring,
    then line-only negation, both flagged the project's own disclaimers.)
    """
    from pathlib import Path
    hits = []
    for path in Path(root).rglob('*.md'):
        if path.name.startswith('._'):
            continue
        try:
            lowered = path.read_text(encoding='utf-8').lower()
        except (ValueError, OSError):
            continue
        for phrase in HARDWARE_BANNED:
            start = 0
            while True:
                pos = lowered.find(phrase, start)
                if pos < 0:
                    break
                window = lowered[max(0, pos - 80):pos + len(phrase)]
                if not any(n in window for n in NEGATIONS):
                    hits.append('%s: %r' % (path, phrase))
                    break
                start = pos + len(phrase)
    return hits
