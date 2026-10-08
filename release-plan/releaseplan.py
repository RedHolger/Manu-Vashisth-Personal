"""Release charter model: an approved baseline kept separate from its changes.

P16-01. This module owns one release charter for a *real* portfolio release
(``charter.json``: the Trio 1 review-bundle release R1-trio1-review). Its whole
reason to exist is one distinction:

    baseline  !=  baseline + approved changes

The ``baseline`` block is the plan as approved on 2026-10-05. The ``changes``
list is every later scope addition, cut, rewire and correction, each carrying a
date, a reason and a source. :func:`apply_changes` folds the changes into a
*new* effective plan and never mutates the baseline block, so the approved plan
stays auditable after any amount of change.

Readiness is deliberately two-valued in provenance:

* :func:`declared_resolve` trusts the ``recorded_exit`` transcribed into the
  charter. It is a *claim* about an artifact.
* ``verify.disk_resolve`` (P16-02) opens the artifact. It is a *measurement*.

Both feed the same reference :func:`project.plan`, so the difference between a
claimed and a measured release is visible in one field.

A task or gate with no evidence is never ready. Vacuous truth is the failure
mode this release plan exists to prevent.
"""
import copy
import json
from pathlib import Path

from project import plan

CHARTER_PATH = Path(__file__).resolve().parent / 'charter.json'

REQUIRED_TASK_KEYS = ('id', 'title', 'depends', 'hours', 'owner', 'evidence')
REQUIRED_CHANGE_KEYS = ('id', 'date', 'type', 'title', 'reason', 'source')
CHANGE_TYPES = frozenset({
    'scope_add', 'scope_cut', 'sequencing_cut', 'tooling_substitution',
    'unplanned_corrective_work', 'process_add', 'process_change', 'rework'})
EVIDENCE_KINDS = frozenset({'exit-status', 'document', 'file'})
EVIDENCE_ROLES = frozenset({'acceptance-run', 'supporting',
                            'retained-failed-attempt'})


class CharterError(ValueError):
    """Raised when a charter violates its own contract."""


# --------------------------------------------------------------------------
# loading and validation
# --------------------------------------------------------------------------
def load_charter(path=None):
    """Load and validate a charter. Returns a plain dict."""
    path = Path(path) if path else CHARTER_PATH
    charter = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_charter(charter)
    return charter


def validate_charter(charter):
    """Structural validation. Raises :class:`CharterError` with a real reason."""
    for key in ('schema_version', 'release', 'baseline', 'changes'):
        if key not in charter:
            raise CharterError('charter is missing %r' % key)
    baseline = charter['baseline']
    for key in ('id', 'status', 'approved_at', 'approved_by', 'scope',
                'milestones', 'gates', 'tasks'):
        if key not in baseline:
            raise CharterError('baseline is missing %r' % key)
    if baseline.get('frozen') is not True:
        raise CharterError('baseline must be marked frozen')
    if not charter['release'].get('solo'):
        raise CharterError('this release is solo; the charter must say so')
    if charter['release'].get('cross_functional_team'):
        raise CharterError('a solo release must not claim a cross-functional team')

    ids = [t['id'] for t in baseline['tasks']]
    if len(set(ids)) != len(ids):
        raise CharterError('duplicate baseline task id')
    for task in baseline['tasks']:
        _validate_task(task)
    projects = set(baseline['scope']['included_projects'])
    for task in baseline['tasks']:
        if task.get('project') and task['project'] not in projects:
            raise CharterError(
                'baseline task %r names project %r outside the approved scope %r'
                % (task['id'], task['project'], sorted(projects)))

    change_ids = [c['id'] for c in charter['changes']]
    if len(set(change_ids)) != len(change_ids):
        raise CharterError('duplicate change id')
    seen_tasks = set(ids)
    for change in charter['changes']:
        _validate_change(change, seen_tasks)
        for task in change.get('adds_tasks', []):
            seen_tasks.add(task['id'])
        for task_id in change.get('removes_tasks', []):
            seen_tasks.discard(task_id)
    return True


def _validate_task(task):
    for key in REQUIRED_TASK_KEYS:
        if key not in task:
            raise CharterError('task %r is missing %r' % (task.get('id'), key))
    if not isinstance(task['hours'], (int, float)) or task['hours'] < 0:
        raise CharterError('task %r has an invalid hours value' % task['id'])
    if not isinstance(task['owner'], str) or not task['owner']:
        raise CharterError('task %r has no owner' % task['id'])
    if not task.get('hours_basis'):
        raise CharterError(
            'task %r declares hours without an hours_basis; estimates must be '
            'labelled as estimates' % task['id'])
    for spec in task['evidence']:
        _validate_evidence_spec(spec, task['id'])
    if task['evidence'] and not required_specs(task['evidence']):
        raise CharterError(
            'task %r declares evidence but none of it is required, so nothing '
            'could ever make it ready' % task['id'])


def required_specs(specs):
    """The specs that actually gate readiness."""
    return [s for s in specs if s.get('required', True)]


def _validate_evidence_spec(spec, owner_id):
    if not isinstance(spec, dict) or not spec.get('path'):
        raise CharterError('task %r has a malformed evidence entry' % owner_id)
    if spec.get('kind') not in EVIDENCE_KINDS:
        raise CharterError('task %r has evidence kind %r'
                           % (owner_id, spec.get('kind')))
    role = spec.get('role', 'acceptance-run')
    if role not in EVIDENCE_ROLES:
        raise CharterError('task %r has evidence role %r' % (owner_id, role))
    if spec['kind'] == 'exit-status':
        if 'expect' not in spec or 'recorded_exit' not in spec:
            raise CharterError(
                'exit-status evidence on %r needs both expect and recorded_exit'
                % owner_id)
        if role == 'retained-failed-attempt' and spec['expect'] == 0:
            raise CharterError(
                'evidence on %r is labelled a retained failed attempt but '
                'expects exit 0; a laundered failure is not evidence'
                % owner_id)
    if spec.get('required') is False and role == 'acceptance-run':
        raise CharterError(
            'evidence on %r is an acceptance run and cannot be optional'
            % owner_id)


def _validate_change(change, known_tasks):
    for key in REQUIRED_CHANGE_KEYS:
        if key not in change:
            raise CharterError('change %r is missing %r'
                               % (change.get('id'), key))
    if change['type'] not in CHANGE_TYPES:
        raise CharterError('change %r has unknown type %r'
                           % (change['id'], change['type']))
    if len(change['reason']) < 20:
        raise CharterError('change %r has no substantive reason' % change['id'])
    if not isinstance(change['source'], dict) or not change['source'].get('document'):
        raise CharterError('change %r has no source document' % change['id'])
    if change.get('baseline_modified'):
        raise CharterError(
            'change %r claims to modify the baseline; scope changes are recorded '
            'as changes, never as edits to the approved baseline' % change['id'])
    for task in change.get('adds_tasks', []):
        _validate_task(task)
        if task['id'] in known_tasks:
            raise CharterError('change %r re-adds existing task %r'
                               % (change['id'], task['id']))
    for task_id in change.get('removes_tasks', []):
        if task_id not in known_tasks:
            raise CharterError('change %r removes unknown task %r'
                               % (change['id'], task_id))
    for rewire in change.get('rewires', []):
        if rewire.get('task') not in known_tasks:
            raise CharterError('change %r rewires unknown task %r'
                               % (change['id'], rewire.get('task')))


# --------------------------------------------------------------------------
# baseline vs effective
# --------------------------------------------------------------------------
def baseline(charter):
    """A deep copy of the approved baseline. Callers cannot mutate the original."""
    return copy.deepcopy(charter['baseline'])


def apply_changes(charter, through=None):
    """Fold changes into a new effective plan. The baseline block is untouched.

    ``through`` optionally limits the fold to changes up to and including that
    change id, so an intermediate point in the release can be replayed.
    """
    effective = copy.deepcopy(charter['baseline'])
    effective.pop('frozen', None)
    effective['derived_from_baseline'] = charter['baseline']['id']
    effective['baseline_task_count'] = len(charter['baseline']['tasks'])
    effective['baseline_gate_count'] = len(charter['baseline']['gates'])
    tasks = {t['id']: t for t in effective['tasks']}
    gates = [(g['id'], g) for g in effective['gates']]
    gate_index = dict(gates)
    applied = []

    for change in charter['changes']:
        applied.append(change['id'])
        for task_id in change.get('removes_tasks', []):
            tasks.pop(task_id, None)
        for task in change.get('adds_tasks', []):
            new_task = copy.deepcopy(task)
            new_task['added_by'] = change['id']
            tasks[new_task['id']] = new_task
        for rewire in change.get('rewires', []):
            target = tasks.get(rewire['task'])
            if target is None:
                raise CharterError('change %r rewires removed task %r'
                                   % (change['id'], rewire['task']))
            target['depends'] = list(rewire['depends'])
            target['rewired_by'] = change['id']
        for gate in change.get('adds_gates', []):
            new_gate = copy.deepcopy(gate)
            new_gate['added_by'] = change['id']
            if new_gate['id'] in gate_index:
                raise CharterError('change %r re-adds gate %r'
                                   % (change['id'], new_gate['id']))
            gate_index[new_gate['id']] = new_gate
            gates.append((new_gate['id'], new_gate))
        if through is not None and change['id'] == through:
            break

    # Dependencies on removed tasks are dropped rather than left dangling; the
    # reference plan() would otherwise raise 'missing prerequisite'.
    for task in tasks.values():
        task['depends'] = [d for d in task['depends'] if d in tasks]
        task.setdefault('added_by', 'baseline')
    for gate in gate_index.values():
        gate['tasks'] = [t for t in gate.get('tasks', []) if t in tasks]

    effective['tasks'] = _stable_order(tasks.values())
    effective['gates'] = [gate_index[gid] for gid, _ in gates
                          if gid in gate_index]
    effective['applied_changes'] = applied
    return effective


def _stable_order(tasks):
    """Insertion-stable order: dependencies always appear before dependents."""
    remaining = list(tasks)
    ordered, placed = [], set()
    while remaining:
        progress = False
        for task in list(remaining):
            if all(d in placed for d in task['depends']):
                ordered.append(task)
                placed.add(task['id'])
                remaining.remove(task)
                progress = True
        if not progress:
            raise CharterError('dependency cycle among %r'
                               % [t['id'] for t in remaining])
    return ordered


def scope_diff(charter):
    """Exactly what distinguishes the approved baseline from the current plan."""
    effective = apply_changes(charter)
    base_ids = {t['id'] for t in charter['baseline']['tasks']}
    eff_ids = {t['id'] for t in effective['tasks']}
    base_projects = {t['project'] for t in charter['baseline']['tasks']
                     if t.get('project')}
    eff_projects = {t['project'] for t in effective['tasks'] if t.get('project')}
    return {
        'baseline_id': charter['baseline']['id'],
        'baseline_tasks': len(base_ids),
        'effective_tasks': len(eff_ids),
        'tasks_only_in_baseline': sorted(base_ids - eff_ids),
        'tasks_only_in_effective': sorted(eff_ids - base_ids),
        'projects_only_in_baseline': sorted(base_projects - eff_projects),
        'projects_only_in_effective': sorted(eff_projects - base_projects),
        'changes_applied': list(effective['applied_changes']),
        'task_provenance': {t['id']: t['added_by'] for t in effective['tasks']},
        'gate_provenance': {g['id']: g.get('added_by', 'baseline')
                            for g in effective['gates']},
        'baseline_projects': sorted(base_projects),
        'effective_projects': sorted(eff_projects),
    }


# --------------------------------------------------------------------------
# readiness resolution
# --------------------------------------------------------------------------
def declared_resolve(spec, root=None):
    """Trust the charter's transcribed ``recorded_exit``. A claim, not a check.

    Returns ``(ok, verified_paths, source)``. ``verified_paths`` lists the paths
    the charter *asserts* exist; nothing is opened.
    """
    if spec['kind'] == 'exit-status':
        ok = spec.get('recorded_exit') == spec.get('expect')
    else:
        ok = True
    return ok, [spec['path']], 'declared'


def resolve_task(task, resolve):
    """Resolve one task's evidence. No evidence at all is never ok.

    Only ``required`` artifacts gate readiness. Retained failed attempts are
    verified too - and a retained attempt that records success is a defect -
    but they are supplementary, not gating.
    """
    specs = task.get('evidence') or []
    if not specs:
        return {'ok': False, 'paths': [], 'source': 'none',
                'reason': task.get('no_artifact_reason')
                or 'no evidence declared'}
    results = list(zip(specs, (resolve(spec) for spec in specs)))
    gating = [(s, r) for s, r in results if s.get('required', True)]
    if not gating:
        return {'ok': False, 'paths': [], 'source': 'none',
                'reason': 'no required evidence; optional artifacts alone '
                          'cannot make a task ready'}
    ok = all(r[0] for _, r in gating)
    paths = sorted({p for _, r in results if r[0] for p in r[1]})
    sources = {r[2] for _, r in results}
    return {'ok': ok, 'paths': paths,
            'source': 'mixed' if len(sources) > 1 else sources.pop(),
            'reason': None if ok else 'a required artifact failed resolution'}


def tasks_for_plan(tasks, resolve=declared_resolve):
    """Build the input list for the reference :func:`project.plan`.

    ``done`` and ``evidence`` are *derived* from the resolver. They are never
    read from a hand-checked boolean in the charter.
    """
    out = []
    for task in tasks:
        result = resolve_task(task, resolve)
        out.append({'id': task['id'],
                    'depends': list(task['depends']),
                    'hours': task['hours'],
                    'owner': task['owner'],
                    'done': bool(result['ok']),
                    'evidence': list(result['paths'])})
    return out


def plan_baseline(charter, resolve=declared_resolve):
    """Reference plan() over the approved baseline, exactly as approved."""
    base = charter['baseline']
    result = plan(tasks_for_plan(base['tasks'], resolve))
    result['source'] = 'baseline'
    result['resolver'] = resolve.__name__
    result['ready_all'] = all(result['ready'].values())
    result['not_ready'] = sorted(i for i, ok in result['ready'].items() if not ok)
    return result


def plan_effective(charter, resolve=declared_resolve, through=None):
    """Reference plan() over baseline + applied changes."""
    effective = apply_changes(charter, through=through)
    result = plan(tasks_for_plan(effective['tasks'], resolve))
    result['source'] = 'effective'
    result['resolver'] = resolve.__name__
    result['ready_all'] = all(result['ready'].values())
    result['not_ready'] = sorted(i for i, ok in result['ready'].items() if not ok)
    result['applied_changes'] = effective['applied_changes']
    return result


def documented_effort_ranges(charter):
    """Every documented planning range the charter is answerable to.

    The baseline contributes its own approved range; each scope change may
    contribute the documented ranges of the projects it adds, so the total is
    the sum of ranges that were actually written down somewhere.
    """
    estimate = charter['baseline']['effort_estimate']
    ranges = [{'scope': 'baseline',
               'source': estimate['source'],
               'hours': list(estimate['documented_range_hours'])}]
    for change in charter['changes']:
        for project, hours in sorted(
                change.get('adds_documented_effort_range_hours', {}).items()):
            ranges.append({'scope': change['id'], 'project': project,
                           'source': change.get('documented_range_source',
                                                'kit SPEC.md planning effort'),
                           'hours': list(hours)})
    return ranges


def estimate_within_documented_range(charter):
    """Compare the effective critical-path estimate with the documented ranges."""
    ranges = documented_effort_ranges(charter)
    low = sum(r['hours'][0] for r in ranges)
    high = sum(r['hours'][1] for r in ranges)
    hours = plan_effective(charter)['estimated_hours']
    return {'ranges': ranges, 'low': low, 'high': high,
            'effective_estimated_hours': hours,
            'baseline_estimated_hours': plan_baseline(charter)['estimated_hours'],
            'within': low <= hours <= high}


def milestones_with_actuals(charter):
    """Milestones as declared, with an explicit status for the unmet ones."""
    out = []
    for milestone in charter['baseline']['milestones']:
        record = dict(milestone)
        record['has_actual_commit'] = bool(milestone.get('actual_commit'))
        if record['status'] == 'ACHIEVED' and not record['has_actual_commit']:
            raise CharterError(
                'milestone %r claims ACHIEVED without an actual_commit'
                % milestone['id'])
        if record['status'] == 'NOT_ACHIEVED' and record['has_actual_commit']:
            raise CharterError(
                'milestone %r claims NOT_ACHIEVED but names a commit'
                % milestone['id'])
        out.append(record)
    return out
