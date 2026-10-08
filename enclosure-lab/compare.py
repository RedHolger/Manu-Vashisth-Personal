"""Revision comparison for EnclosureLab (P22-03): fit, assembly, thermal.

Compares v1 (open-top) vs v2 (lidded) on assumed geometry only. Thermal
entries are DOCUMENTED ASSUMPTIONS with boundary conditions — never
simulation results. `banned_claim_scan()` refuses uncalibrated validation
language (affirmative 'validated'/'verified fit'/'thermal simulation passed'
without a qualifier); assumption-tagged statements pass.
"""
import enclosure

BANNED_CLAIMS = ['validated', 'verified fit', 'thermal simulation passed',
                 'proven fit', 'certified', 'simulation shows it works']
QUALIFIERS = ['not ', 'assumption', 'assumed', 'unvalidated', 'no ',
              'refused', 'blocked']


def compare_revisions():
    p = enclosure.enclosure_params()
    fit = enclosure.check_fit()
    v1_bom = enclosure.bom('v1')
    v2_bom = enclosure.bom('v2')
    return {
        'fit': {'clearances_mm': {'x': fit['clear_x'], 'y': fit['clear_y'],
                                  'z': fit['clear_z']},
                'verdict': 'same cavity both revs; clearances meet R1 on '
                           'ASSUMED dims (not a fit claim)',
                'authoritative': False},
        'assembly': {'v1_steps': ['place board on standoffs',
                                  'fasten 4x M2.5'],
                     'v2_steps': ['place board on standoffs',
                                  'fasten 4x M2.5', 'seat lid',
                                  'fasten 4x M3 into inserts'],
                     'v1_bom_lines': len(v1_bom), 'v2_bom_lines': len(v2_bom),
                     'verdict': 'v2 adds lid alignment + 4 screws; '
                                'assembly untested (no prototype)'},
        'thermal': {'v1_assumption': 'open top convects better (ASSUMED; '
                                     'no mesh, no solver)',
                    'v2_assumption': 'lid traps heat; 3 W assumed, 25 C '
                                     'ambient assumed (ASSUMED; no mesh, '
                                     'no solver)',
                    'verdict': 'assumptions documented with boundary '
                               'conditions; no simulation run, no result '
                               'claimed'},
    }


def banned_claim_scan(text):
    """Affirmative validation claims without a qualifier; returns hits."""
    lowered = text.lower()
    hits = []
    for claim in BANNED_CLAIMS:
        start = 0
        while True:
            pos = lowered.find(claim, start)
            if pos < 0:
                break
            window = lowered[max(0, pos - 60):pos + len(claim)]
            if not any(q in window for q in QUALIFIERS):
                hits.append(claim)
                break
            start = pos + len(claim)
    return hits
