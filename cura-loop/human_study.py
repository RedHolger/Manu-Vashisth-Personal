"""Human-annotation timing harness for CuraLoop (P10-04, optional).

The whole point of this card is a clean, enforced separation between two
quantities that must never be conflated:

* ``measured_human_time`` — real wall-clock seconds a *consenting* annotator
  spent on a label, captured by a stopwatch around the actual action.
* ``synthetic_proxy_cost`` — the simulated cost used by the P10-03 experiment
  (an acquisition/wall-clock proxy), which is *not* human time.

Guardrails:

* Recording measured human time requires an explicit consent record; without
  it the session is a ``DRY_RUN`` and cannot contribute to a human claim.
* The two costs live in different fields with different ``source`` tags. A
  report never sums them, and ``combined_cost()`` raises rather than silently
  mixing a proxy for a measurement.
* No participants means ``participants_measured == 0`` and status
  ``BLOCKED_NO_CONSENTING_PARTICIPANTS`` — the tooling can be VERIFIED while
  the human study stays honestly blocked.
"""
import time

STATUS_BLOCKED = 'BLOCKED_NO_CONSENTING_PARTICIPANTS'
STATUS_DRY_RUN = 'DRY_RUN'
STATUS_MEASURED = 'MEASURED'


class ConsentError(RuntimeError):
    """Raised when measured human time is requested without consent."""


class CostMixingError(RuntimeError):
    """Raised on any attempt to combine human time with synthetic proxy cost."""


def time_action(action, *args, **kwargs):
    """Run ``action`` and return ``(result, elapsed_seconds)`` (real clock)."""
    start = time.perf_counter()
    result = action(*args, **kwargs)
    return result, time.perf_counter() - start


class AnnotationSession:
    """One annotator's timed labeling session."""

    def __init__(self, annotator_id, consent=None, clock=time.perf_counter):
        self.annotator_id = annotator_id
        self.consent = consent            # dict {granted, form, at} or None
        self.clock = clock
        self.records = []                 # measured human-time records
        self.dry_run_records = []         # timing without consent (not human data)

    @property
    def has_consent(self):
        return bool(self.consent and self.consent.get('granted'))

    def record_label(self, item_id, value, action=None):
        """Time one labeling action as measured human time.

        Without consent the timing is stored as a dry-run diagnostic and is
        explicitly *not* counted as a participant measurement.
        """
        action = action or (lambda: value)
        result, elapsed = time_action(action)
        record = {'id': item_id, 'value': value, 'seconds': elapsed,
                  'annotator_id': self.annotator_id,
                  'source': 'stopwatch'}
        if self.has_consent:
            self.records.append(record)
        else:
            record['source'] = 'dry-run-stopwatch'
            self.dry_run_records.append(record)
        return record

    @property
    def measured_human_seconds(self):
        return sum(r['seconds'] for r in self.records)

    @property
    def labels_measured(self):
        return len(self.records)


class SyntheticProxyCost:
    """The simulation's cost proxy — tagged so it is never read as human."""

    def __init__(self, seconds_per_label):
        self.seconds_per_label = seconds_per_label
        self.source = 'simulation'

    def for_labels(self, n):
        return {'seconds': self.seconds_per_label * n,
                'source': self.source, 'n_labels': n}


class HumanStudy:
    """Aggregates sessions; enforces the human-vs-proxy boundary."""

    def __init__(self, proxy=None):
        self.sessions = []
        self.proxy = proxy or SyntheticProxyCost(0.0)

    def add_session(self, session):
        self.sessions.append(session)
        return session

    @property
    def consenting_sessions(self):
        return [s for s in self.sessions if s.has_consent]

    @property
    def participants_measured(self):
        return len({s.annotator_id for s in self.consenting_sessions
                    if s.labels_measured > 0})

    def measured_human_time(self):
        """Real seconds from consenting annotators only."""
        sessions = self.consenting_sessions
        return {'seconds': sum(s.measured_human_seconds for s in sessions),
                'labels': sum(s.labels_measured for s in sessions),
                'participants': self.participants_measured,
                'source': 'stopwatch'}

    def synthetic_proxy_cost(self, n_labels):
        return self.proxy.for_labels(n_labels)

    def combined_cost(self, *args, **kwargs):
        raise CostMixingError(
            'measured human time and synthetic proxy cost must stay separate; '
            'refusing to combine them')

    def status(self):
        if self.participants_measured == 0:
            return STATUS_BLOCKED
        return STATUS_MEASURED

    def report(self):
        human = self.measured_human_time()
        return {
            'human_study_status': self.status(),
            'participants_measured': human['participants'],
            'measured_human_time': human,               # source: stopwatch
            'synthetic_proxy_cost': self.proxy.for_labels(human['labels']),
            'dry_run_labels': sum(len(s.dry_run_records) for s in self.sessions),
            'note': ('measured_human_time and synthetic_proxy_cost are distinct '
                     'fields with distinct sources and are never summed'),
        }
