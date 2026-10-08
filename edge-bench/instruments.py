"""Instrument probe for EdgeBench (P20-04): power/thermal honestly BLOCKED.

Probes for usable power/thermal instruments WITHOUT executing anything
privileged (no sudo, no sampling daemons). Nothing usable exists here, so
measured watts/temperature are BLOCKED and stay null. `measured_watts()` and
`measured_temperature()` raise instead of returning an estimate — estimates
can never be read out of a measured field.
"""
import shutil


class BlockedError(RuntimeError):
    pass


def probe_power():
    candidates = {'powermetrics': shutil.which('powermetrics'),
                  'powercap': '/sys/class/powercap'}
    usable = False
    reason = ('no usable power instrument (powermetrics needs privilege and '
              'is not executed here; no powercap on this host)')
    return {'available': usable, 'status': 'BLOCKED', 'candidates': candidates,
            'reason': reason}


def probe_thermal():
    return {'available': False, 'status': 'BLOCKED',
            'reason': 'no temperature sensor interface usable from user space '
                      'here; no thermal validation possible'}


def manifest():
    return {'power_watts': None, 'temperature_c': None,
            'power': probe_power(), 'thermal': probe_thermal()}


def measured_watts():
    raise BlockedError('no power instrument; measured watts BLOCKED '
                       '(estimates must never fill this field)')


def measured_temperature():
    raise BlockedError('no thermal instrument; measured temperature BLOCKED '
                       '(estimates must never fill this field)')
