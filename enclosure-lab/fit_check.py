"""Prototype fit procedure for EnclosureLab (P22-04): BLOCKED, worksheet ready.

No prototype exists, so no fit is verified. This module is the procedure +
blank worksheet + a harness that ACCEPTS real measurements when they exist
and REFUSES to pass without them (`verify_fit()` raises `BlockedError` on an
empty worksheet). Even with measurements, the verdict compares against
ASSUMED dims (not authoritative) and says so.
"""
import enclosure

WORKSHEET_ITEMS = [
    ('outer_width', 'caliper', '±0.2'),
    ('outer_length', 'caliper', '±0.2'),
    ('lid_gap', 'feeler gauge', '≤0.3 (assumed)'),
    ('hole_1_x', 'caliper/CMM', '±0.1 (assumed)'),
    ('cutout_A_clearance', 'caliper', '+0.5 min (assumed)'),
    ('defects', 'visual', 'log only'),
]


class BlockedError(RuntimeError):
    pass


class FitWorksheet:
    """Blank worksheet that only passes on real recorded measurements."""

    def __init__(self):
        self.measurements = {}   # item -> {value, instrument, date_utc}

    def blank(self):
        return [{'item': item, 'instrument': inst, 'tolerance': tol,
                 'value': None} for item, inst, tol in WORKSHEET_ITEMS]

    def record(self, item, value, instrument, date_utc):
        valid = {i for i, _, _ in WORKSHEET_ITEMS}
        if item not in valid:
            raise KeyError('unknown worksheet item %r' % (item,))
        if not isinstance(value, (int, float)):
            raise ValueError('measured value must be numeric')
        if item == 'defects' and not isinstance(value, str):
            raise ValueError('defects log as text')
        self.measurements[item] = {'value': value, 'instrument': instrument,
                                   'date_utc': date_utc}
        return self.measurements[item]

    def verify_fit(self):
        if not self.measurements:
            raise BlockedError('no prototype measurements recorded; physical '
                               'fit is BLOCKED (no prototype fabricated)')
        params = enclosure.enclosure_params()
        findings = []
        ow = self.measurements.get('outer_width', {}).get('value')
        if ow is not None:
            findings.append({'item': 'outer_width', 'measured': ow,
                             'assumed_nominal': params['outer_width'],
                             'within_assumed_tol': abs(
                                 ow - params['outer_width']) <= 0.2})
        return {'status': 'MEASURED_VS_ASSUMED (not authoritative)',
                'findings': findings,
                'n_measured': len(self.measurements)}
