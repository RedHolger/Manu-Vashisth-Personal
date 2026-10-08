"""Runbook evaluation for PacketLab (P19-04): hypotheses + timing split.

Troubleshooting is logged as hypotheses with evidence, verdicts and
reasoning time. WRONG hypotheses stay in the log as refuted (never deleted).
Collection time (parser runtime, MEASURED) is stored separately from human
reasoning time (BLOCKED with no analyst — claiming it raises). Reports cover
controlled-lab evidence only.
"""
import time

import capture
import project
import scenarios


class UnmeasuredError(RuntimeError):
    pass


class HypothesisLog:
    """Append-only hypotheses; refuted ones are retained, not removed."""

    def __init__(self, case):
        self.case = case
        self.entries = []

    def hypothesize(self, text, evidence=()):
        self.entries.append({'hypothesis': text, 'evidence': list(evidence),
                             'verdict': 'open'})
        return self.entries[-1]

    def resolve(self, index, verdict):
        if verdict not in ('confirmed', 'refuted'):
            raise ValueError('verdict must be confirmed/refuted')
        self.entries[index]['verdict'] = verdict
        return self.entries[index]

    def wrong_retained(self):
        return [e for e in self.entries if e['verdict'] == 'refuted']


class Timing:
    """Collection time (measured) vs reasoning time (human; BLOCKED here)."""

    def __init__(self):
        self.collection_seconds = None
        self.reasoning_seconds = None

    def measure_collection(self, fn, *args):
        start = time.perf_counter()
        out = fn(*args)
        self.collection_seconds = time.perf_counter() - start
        return out

    def record_reasoning(self, seconds=None):
        if seconds is None:
            raise UnmeasuredError(
                'no analyst timing taken; human reasoning time is BLOCKED '
                '(refusing to invent it)')
        self.reasoning_seconds = seconds

    def split(self):
        return {'collection_seconds_measured': self.collection_seconds,
                'reasoning_seconds': self.reasoning_seconds,
                'reasoning_status': 'BLOCKED_NO_ANALYST_TIMING'
                if self.reasoning_seconds is None else 'MEASURED'}


def troubleshoot(case, fixture_dir):
    """Runbook walkthrough of one fixture: layered checklist + hypotheses.

    Uses the reference layered `diagnose()` on evidence derived from the
    parsed capture, logs one wrong hypothesis first (retained as refuted),
    then the confirmed one. Collection time measured; reasoning unmeasured.
    """
    timing = Timing()
    parsed = timing.measure_collection(capture.parse_file,
                                       '%s/%s.pkt' % (fixture_dir, case))
    truth = scenarios.GROUND_TRUTH[case]
    log = HypothesisLog(case)
    # A plausible wrong first guess, kept refuted (runbook honesty).
    wrong = {'dns-fail': 'route blackhole (no replies seen)',
             'route-blackhole': 'DNS failure (name unknown)',
             'mtu-clamp': 'service down (big sends stall)',
             'conn-timeout': 'route blackhole (no data flows)'}[case]
    log.hypothesize(wrong)
    log.resolve(0, 'refuted')
    layer_ok = {'dns': ('dns', True), 'route': ('route', False),
                'tcp': ('tcp', False),
                'application': ('application', False)}[truth['layer']]
    evidence = {layer: None for layer in ('dns', 'route', 'tcp',
                                          'application')}
    evidence[layer_ok[0]] = layer_ok[1]
    diagnosis = project.diagnose(evidence)
    log.hypothesize('ground truth: %s (%s layer)' % (truth['fault'],
                                                     truth['layer']))
    log.resolve(1, 'confirmed')
    return {'case': case, 'ground_truth': truth, 'diagnosis': diagnosis,
            'hypotheses': log.entries,
            'wrong_retained': len(log.wrong_retained()),
            'timing': timing.split(), 'parsed_packets': parsed['n_packets']}
