"""Artifact verification: readiness measured from disk, never declared (P16-02).

The reference ``project.plan`` computes readiness from ``owner``/``evidence``/
``done``. In the source-kit reference those three are hand-written booleans, and
its own note says so: *"Evidence references are declared, not
content-verified."* This module removes that gap for the real charter.

An :class:`ArtifactVerifier` opens every referenced artifact and answers four
questions about it:

1. does the path exist inside the repository root (and not escape it)?
2. for ``document``/``file`` kinds, is it non-empty?
3. for ``exit-status``, does the recorded status parse, and does the required
   key equal the expected value?
4. what is its size and sha256 right now?

Its ``resolve`` method has the same signature as
``releaseplan.declared_resolve``, so it drops straight into
``releaseplan.tasks_for_plan`` and the unmodified reference ``plan``. The only
thing that changes is provenance: ``source`` becomes ``verified``.

Three rules make a false "ready" structurally impossible:

* **No evidence is never ready.** A task or gate with an empty artifact list is
  ``ok=False``; vacuous truth is refused.
* **One failed artifact fails the task.** Existence, emptiness and exit-status
  are conjoined, not averaged.
* **Ambiguity fails closed.** An ``exit-status`` file carrying several
  ``key=value`` pairs without a declared ``exit_key`` is not guessed at.

Readiness then still propagates through the reference DAG, so a task whose own
artifacts are perfect but whose prerequisite is blocked is not ready either.
"""
import hashlib
import json
import time
from pathlib import Path

from project import plan
import releaseplan as rp

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class ArtifactVerifier:
    """Verifies charter evidence against the real filesystem."""

    def __init__(self, root=None, follow_symlinks=False):
        self.root = Path(root).resolve() if root else DEFAULT_ROOT
        self.follow_symlinks = follow_symlinks
        self.records = []

    # -- path safety -------------------------------------------------------
    def resolve_path(self, relpath):
        """Return (absolute_path, error). Never escapes the repository root."""
        parts = str(relpath).split('/')
        if str(relpath).startswith('/') or '..' in parts:
            return None, 'path escapes the repository root'
        candidate = (self.root / relpath)
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            return None, 'unresolvable path: %s' % exc
        if not self.follow_symlinks and resolved.is_symlink():
            return resolved, None
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return None, 'resolved path leaves the repository root'
        return resolved, None

    # -- exit-status parsing ----------------------------------------------
    @staticmethod
    def parse_exit_status(text):
        """Parse an exit-status file into ``{key: int}``.

        Two real formats occur in this repository:

        * a bare integer, e.g. ``0`` -> ``{'exit': 0}``
        * ``key=value`` lines, e.g. ``assertions_passed=40`` /
          ``assertions_failed=0`` / ``exit=0``

        Raises ``ValueError`` when the file denotes no integer at all.
        """
        values = {}
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            raise ValueError('empty exit-status file')
        if len(lines) == 1 and '=' not in lines[0]:
            try:
                return {'exit': int(lines[0])}
            except ValueError:
                raise ValueError('exit-status file is not an integer: %r'
                                 % lines[0])
        for line in lines:
            key, sep, value = line.partition('=')
            if not sep:
                raise ValueError('unparseable exit-status line %r' % line)
            try:
                values[key.strip()] = int(value.strip())
            except ValueError:
                raise ValueError('non-integer exit-status value %r' % line)
        return values

    # -- single artifact ---------------------------------------------------
    def verify_artifact(self, spec):
        """Verify one evidence spec. Returns a record; never raises."""
        record = {'path': spec['path'], 'kind': spec.get('kind'),
                  'role': spec.get('role', 'acceptance-run'),
                  'required': spec.get('required', True),
                  'exists': False, 'ok': False, 'reason': None,
                  'size_bytes': None, 'sha256': None,
                  'recorded_status': None, 'expected': spec.get('expect'),
                  'exit_key': spec.get('exit_key')}
        path, error = self.resolve_path(spec['path'])
        if error:
            record['reason'] = error
            self.records.append(record)
            return record
        record['absolute_path'] = str(path)
        if not path.exists():
            record['reason'] = 'missing: no such file or directory'
            self.records.append(record)
            return record
        record['exists'] = True
        if path.is_dir():
            record['reason'] = 'expected a file, found a directory'
            self.records.append(record)
            return record
        try:
            data = path.read_bytes()
        except OSError as exc:
            record['reason'] = 'unreadable: %s' % exc
            self.records.append(record)
            return record
        record['size_bytes'] = len(data)
        record['sha256'] = hashlib.sha256(data).hexdigest()

        kind = spec.get('kind')
        if kind in ('document', 'file') and len(data) == 0:
            record['reason'] = 'empty artifact'
            self.records.append(record)
            return record
        if kind == 'exit-status':
            try:
                values = self.parse_exit_status(data.decode('utf-8',
                                                            errors='replace'))
            except (ValueError, UnicodeDecodeError) as exc:
                record['reason'] = 'unparseable exit-status: %s' % exc
                self.records.append(record)
                return record
            record['recorded_status'] = values
            key = spec.get('exit_key')
            expect = spec.get('expect', 0)
            if key is None:
                if len(values) == 1:
                    key = next(iter(values))
                elif 'exit' in values:
                    key = 'exit'
                else:
                    record['reason'] = (
                        'ambiguous exit-status file with keys %s and no '
                        'declared exit_key; refusing to guess' % sorted(values))
                    self.records.append(record)
                    return record
            if key not in values:
                record['reason'] = ('exit_key %r absent; file records %s'
                                    % (key, sorted(values)))
                self.records.append(record)
                return record
            if values[key] != expect:
                record['reason'] = ('%s=%r, expected %r'
                                    % (key, values[key], expect))
                self.records.append(record)
                return record
        record['ok'] = True
        self.records.append(record)
        return record

    # -- resolver protocol used by releaseplan -----------------------------
    def resolve(self, spec):
        """``(ok, paths, 'verified')`` - matches releaseplan.declared_resolve."""
        record = self.verify_artifact(spec)
        return record['ok'], ([spec['path']] if record['exists'] else []), \
            'verified'

    # -- task / gate level -------------------------------------------------
    def verify_task(self, task):
        specs = task.get('evidence') or []
        artifacts = [self.verify_artifact(spec) for spec in specs]
        pairs = list(zip(specs, artifacts))
        gating = [(s, a) for s, a in pairs if s.get('required', True)]
        optional = [(s, a) for s, a in pairs if not s.get('required', True)]
        if not specs:
            ok, reason = False, (task.get('no_artifact_reason')
                                 or 'no evidence declared')
        elif not gating:
            ok, reason = False, ('no required evidence; optional artifacts '
                                 'alone cannot make a task ready')
        else:
            ok = all(a['ok'] for _, a in gating)
            reason = None if ok else '; '.join(
                '%s: %s' % (a['path'], a['reason']) for _, a in gating
                if not a['ok'])
        # A retained failed attempt that actually passed is a defect: it means
        # the "failure" on display is not the run that was described.
        laundered = [a['path'] for s, a in optional
                     if s.get('role') == 'retained-failed-attempt'
                     and s.get('kind') == 'exit-status' and a['ok']
                     and s.get('expect') == 0]
        return {'id': task['id'], 'ok': ok, 'reason': reason,
                'owner': task.get('owner'),
                'artifacts_total': len(artifacts),
                'artifacts_ok': sum(1 for a in artifacts if a['ok']),
                'required_total': len(gating),
                'required_ok': sum(1 for _, a in gating if a['ok']),
                'optional_total': len(optional),
                'retained_failures_laundered': laundered,
                'artifacts': artifacts}

    def verify_gate(self, gate):
        specs = gate.get('artifacts') or []
        artifacts = [self.verify_artifact(spec) for spec in specs]
        pairs = list(zip(specs, artifacts))
        gating = [(s, a) for s, a in pairs if s.get('required', True)]
        human = bool(gate.get('requires_human_decision'))
        if human:
            ok = False
            reason = gate.get('reason_no_artifact') or (
                'human decision gate: cannot be satisfied by automation')
        elif not specs:
            ok, reason = False, ('gate declares no artifact; refusing '
                                 'vacuous truth')
        elif not gating:
            ok, reason = False, 'gate has no required artifact'
        else:
            ok = all(a['ok'] for _, a in gating)
            reason = None if ok else '; '.join(
                '%s: %s' % (a['path'], a['reason']) for _, a in gating
                if not a['ok'])
        return {'id': gate['id'], 'ok': ok, 'reason': reason,
                'human_decision_required': human,
                'artifacts_total': len(artifacts),
                'artifacts_ok': sum(1 for a in artifacts if a['ok']),
                'required_total': len(gating),
                'required_ok': sum(1 for _, a in gating if a['ok']),
                'artifacts': artifacts}

    # -- whole charter -----------------------------------------------------
    def verify_charter(self, charter, through=None):
        effective = rp.apply_changes(charter, through=through)
        tasks = {t['id']: self.verify_task(t) for t in effective['tasks']}
        gates = {g['id']: self.verify_gate(g) for g in effective['gates']}
        ledger = list(self.records)

        # A second, independent verifier drives releaseplan.tasks_for_plan into
        # the unmodified reference plan(). Two passes over the same artifacts
        # must agree; if they do not, readiness is not a measurement.
        plan_verifier = ArtifactVerifier(self.root)
        planned = plan(rp.tasks_for_plan(effective['tasks'],
                                         plan_verifier.resolve))
        second = {r['path']: r['ok'] for r in plan_verifier.records}
        first = {r['path']: r['ok'] for r in ledger}
        passes_agree = all(second.get(p) == ok for p, ok in first.items()
                           if p in second)

        report = {
            'root': str(self.root),
            'verified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'resolver': 'verified',
            'tasks': tasks,
            'gates': gates,
            'plan': planned,
            'artifacts_total': len(ledger),
            'artifacts_ok': sum(1 for r in ledger if r['ok']),
            'distinct_artifacts': len(first),
            'tasks_ok': sum(1 for t in tasks.values() if t['ok']),
            'tasks_total': len(tasks),
            'gates_ok': sum(1 for g in gates.values() if g['ok']),
            'gates_total': len(gates),
            'ready_all': all(planned['ready'].values()),
            'not_ready': sorted(i for i, ok in planned['ready'].items()
                                if not ok),
            'failures': [{'path': r['path'], 'reason': r['reason']}
                         for r in ledger if not r['ok']],
            'required_failures': sorted({
                r['path'] for r in ledger if not r['ok'] and r['required']}),
            'optional_failures': sorted({
                r['path'] for r in ledger if not r['ok'] and not r['required']}),
            'laundered_failures': sorted({
                p for t in tasks.values()
                for p in t['retained_failures_laundered']}),
            'two_verification_passes_agree': passes_agree,
        }
        # Cross-check: reference readiness must never exceed verification.
        report['readiness_never_exceeds_verification'] = all(
            planned['ready'][task_id] <= result['ok']
            for task_id, result in tasks.items())
        return report


def disk_resolve_factory(root=None):
    """A bare resolver function for callers that only need task readiness."""
    return ArtifactVerifier(root).resolve


def repoint_evidence(charter, task_id, missing_path):
    """Return a charter copy whose ``task_id`` points at a missing artifact.

    Used only to demonstrate the acceptance rule: a failed or missing
    verification cannot appear ready. The real charter on disk is never
    modified.
    """
    import copy
    broken = copy.deepcopy(charter)
    containers = [broken['baseline']['tasks']]
    containers += [c.get('adds_tasks', []) for c in broken['changes']]
    for tasks in containers:
        for task in tasks:
            if task['id'] == task_id:
                task['evidence'] = [{'path': missing_path, 'kind': 'document'}]
                return broken
    raise KeyError('no task %r in the charter' % task_id)


def as_json(report):
    return json.dumps(report, indent=2, sort_keys=True, default=str)
