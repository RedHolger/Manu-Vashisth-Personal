"""Evidence-linked discovery for LaunchLab (P17-01).

Every prioritized opportunity either cites registered REAL evidence (a
portfolio artifact verified by path + sha256) or is explicitly labeled
HYPOTHESIS. An item with neither is rejected — it cannot be prioritized on
nothing. Audience needs stay hypotheses until real interviews exist.
"""
import hashlib
from pathlib import Path

import project

ROOT = Path(__file__).parent.parent


def register_artifact(evidence_id, relpath):
    """Register a real artifact; returns its evidence record."""
    path = ROOT / relpath
    if not path.exists():
        raise FileNotFoundError('evidence artifact missing: %s' % relpath)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'id': evidence_id, 'kind': 'artifact', 'path': relpath,
            'sha256': digest}


def verify(record):
    """Re-check a registered artifact (path + hash)."""
    if record['kind'] != 'artifact':
        return False
    path = ROOT / record['path']
    if not path.exists():
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']


def prioritize_labeled(features, evidence):
    """Rank via the reference scorer, enforcing evidence-or-HYPOTHESIS.

    Each feature needs `evidence` (ids present in `evidence`) or
    `hypothesis: True` (explicitly labeled). A feature with neither raises.
    Returns the ranked list with a `basis` tag per item.
    """
    ids = {e['id'] for e in evidence}
    tagged = []
    for feature in features:
        has_evidence = bool(feature.get('evidence')) and all(
            e in ids for e in feature['evidence'])
        is_hypothesis = bool(feature.get('hypothesis'))
        if not (has_evidence or is_hypothesis):
            raise ValueError('opportunity %r has neither evidence nor an '
                             'explicit HYPOTHESIS label' % feature.get('id'))
        basis = 'evidence' if has_evidence else 'HYPOTHESIS'
        tagged.append(dict(feature, basis=basis))
    # The reference scorer needs evidence ids; hypotheses carry none, so score
    # both kinds through it with the union id set (hypotheses already tagged).
    scored = project.prioritize(
        [dict(f, evidence=list(f.get('evidence', [])) or ['hypothesis-only'])
         if f['basis'] == 'HYPOTHESIS' else f for f in tagged],
        ids | {'hypothesis-only'})
    by_id = {f['id']: f for f in tagged}
    return [dict(s, basis=by_id[s['id']]['basis']) for s in scored]


AUDIENCE = {'audience': 'solo developer shipping a review bundle',
            'problem': 'release readiness is unknown until human review',
            'status': 'HYPOTHESIS until real consenting interviews exist'}


def opportunities():
    return [
        {'id': 'readiness-check', 'reach': 8, 'impact': 3, 'confidence': 0.7,
         'effort': 2, 'evidence': ['p16-charter', 'p16-verify']},
        {'id': 'evidence-bundle', 'reach': 8, 'impact': 2, 'confidence': 0.6,
         'effort': 3, 'evidence': ['p16-charter']},
        {'id': 'pilot-analytics', 'reach': 5, 'impact': 2, 'confidence': 0.3,
         'effort': 4, 'evidence': [], 'hypothesis': True},
        {'id': 'landing-page', 'reach': 6, 'impact': 1, 'confidence': 0.2,
         'effort': 2, 'evidence': [], 'hypothesis': True},
    ]
