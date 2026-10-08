"""Versioned annotation store, budget accounting and review queue (P10-02).

The store is the single source of truth for *acquired* labels. Every change
is an immutable version record carrying ``(id, value, author, at, version)``;
nothing is overwritten in place, so the audit history is append-only.

Two invariants matter for acceptance:

* Every label change has an author, a monotonic timestamp and a version.
* Repeated labels do not inflate the acquired count. Re-submitting the same
  ``(id, value)`` is a no-op that returns the existing version and charges no
  budget; only a *distinct* id raises ``acquired_count``. A correction
  (``id, new_value``) appends a new version but still counts the id once.

Budget is spent only when a *new* id is first labeled, so a caller that
re-labels cannot silently exceed the annotation budget. Time is injectable so
tests and measurements are byte-for-byte reproducible.
"""
import time


class Budget:
    """Fixed annotation budget; only first-time labels charge it."""

    def __init__(self, total):
        if total < 0:
            raise ValueError('budget must be >= 0')
        self.total = total
        self.spent = 0

    @property
    def remaining(self):
        return self.total - self.spent

    def charge(self, amount=1):
        if amount < 0:
            raise ValueError('cannot charge a negative amount')
        if self.spent + amount > self.total:
            raise BudgetExceeded(
                'budget exhausted: spent %d + %d > total %d'
                % (self.spent, amount, self.total))
        self.spent += amount

    def as_dict(self):
        return {'total': self.total, 'spent': self.spent,
                'remaining': self.remaining}


class BudgetExceeded(RuntimeError):
    """Raised when a first-time label would exceed the annotation budget."""


class ReviewQueue:
    """Items flagged for a second look, with an audit trail."""

    def __init__(self):
        self._pending = []          # ordered ids awaiting review
        self._reason = {}           # id -> reason enqueued
        self.resolved = []          # list of resolution records

    def enqueue(self, item_id, reason, at=None):
        at = time.time() if at is None else at
        if item_id in self._pending:
            return False            # already queued; do not duplicate
        self._pending.append(item_id)
        self._reason[item_id] = {'reason': reason, 'at': at}
        return True

    def pending(self):
        return list(self._pending)

    def reason(self, item_id):
        return dict(self._reason[item_id])

    def resolve(self, item_id, reviewer, verdict, at=None):
        if item_id not in self._pending:
            raise KeyError('item %r is not pending review' % (item_id,))
        if verdict not in ('approved', 'corrected', 'rejected'):
            raise ValueError('unknown verdict %r' % (verdict,))
        at = time.time() if at is None else at
        self._pending.remove(item_id)
        record = {'id': item_id, 'reviewer': reviewer, 'verdict': verdict,
                  'at': at, 'reason': self._reason[item_id]['reason']}
        self.resolved.append(record)
        return record


class AnnotationStore:
    """Append-only, versioned label store with budget + review queue."""

    def __init__(self, budget=None, clock=None):
        self._versions = {}         # id -> list of version records
        self._order = []            # ids in first-label order
        self.budget = budget
        self.clock = clock or time.time
        self.review = ReviewQueue()

    def _now(self, at):
        return self.clock() if at is None else at

    def label(self, item_id, value, author, at=None, review=False,
              reason='flagged'):
        """Record a label. Returns ``(version_record, changed_bool)``.

        ``changed`` is True only when this call created a new version. A
        repeated identical label returns the current version and charges
        nothing; a correction appends a version but does not re-charge budget
        because the id was already acquired.
        """
        if not isinstance(author, str) or not author:
            raise ValueError('author is required')
        at = self._now(at)
        history = self._versions.get(item_id)
        if history:
            current = history[-1]
            if current['value'] == value:
                # Repeated label: idempotent, no new version, no budget.
                if review:
                    self.review.enqueue(item_id, reason, at=at)
                return current, False
            if self.budget is not None and self.budget.remaining < 0:
                raise BudgetExceeded('budget already exhausted')
            record = {'id': item_id, 'value': value, 'author': author,
                      'at': at, 'version': current['version'] + 1,
                      'prior_value': current['value']}
            history.append(record)
        else:
            if self.budget is not None:
                self.budget.charge(1)   # first-time acquisition costs budget
            record = {'id': item_id, 'value': value, 'author': author,
                      'at': at, 'version': 1, 'prior_value': None}
            self._versions[item_id] = [record]
            self._order.append(item_id)
        if review:
            self.review.enqueue(item_id, reason, at=at)
        return record, True

    def current(self, item_id):
        history = self._versions.get(item_id)
        return dict(history[-1]) if history else None

    def value(self, item_id):
        record = self.current(item_id)
        return record['value'] if record else None

    def history(self, item_id):
        return [dict(record) for record in self._versions.get(item_id, [])]

    def acquired_ids(self):
        """Distinct ids that carry a current label (repeats collapse)."""
        return list(self._order)

    @property
    def acquired_count(self):
        return len(self._order)

    def labeled_items(self):
        """{id: current_value} for every acquired id."""
        return {item_id: self.value(item_id) for item_id in self._order}

    def audit_trail(self):
        """Flat, ordered list of every version record across all ids."""
        trail = []
        for item_id in self._order:
            trail.extend(self.history(item_id))
        return trail
