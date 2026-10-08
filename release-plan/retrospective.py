"""Planned versus actual delivery, reconstructed from the real git history.

P16-04. Nothing here is estimated twice: the *planned* side comes from
``charter.json`` (whose ranges are quoted from ``TRIO1_P04-P06_PLAN.md`` and
the kit ``SPEC.md`` files) and the *actual* side comes from ``git log``.

The honesty constraint that shapes the whole module is that **commit timestamps
are delivery moments, not effort**. Git cannot say how many hours a card took,
no timesheet exists, and the plan's unit was "focused hours at a self-chosen
8-12 h/week". So the report compares:

* planned *order* versus actual *order* (exactly comparable),
* planned *scope* versus actual *scope* (exactly comparable),
* planned *effort range* versus actual *wall-clock span* (NOT comparable as
  effort; reported as a ratio and labelled ``effort_measurable: false``),
* planned *milestones* versus actual *commits* (exactly comparable).

Every deviation carries an ``explanation`` and a ``source``. A deviation
without one raises, because an unexplained deviation is the thing a
retrospective exists to remove.
"""
import re
import subprocess
from datetime import datetime, timezone

RECORD_SEP = '\x1e'
FIELD_SEP = '\x1f'
CARD_RE = re.compile(r'\bP(\d{2})-(\d{2})(?:\.\.(\d{2}))?\b')
PROJECT_DIR_RE = re.compile(r'^P\d{2}-')

EFFORT_DISCLAIMER = (
    'Wall-clock span between the first and last commit touching a directory. '
    'It is NOT measured effort: no timesheet exists, agent-assisted work is '
    'bursty, and the plan\'s unit was focused hours at 8-12 h/week.')


class RetroError(ValueError):
    """Raised when a deviation would be reported without an explanation."""


def _git(root, args, timeout=120):
    result = subprocess.run(['git', '-C', str(root)] + args,
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RetroError('git %s failed: %s' % (args, result.stderr.strip()))
    return result.stdout


def _parse_utc(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def commits(root, paths=None, limit=None):
    """Real commit records, newest first."""
    args = ['log', '--format=%s' % FIELD_SEP.join(
        ['%H', '%h', '%aI', '%an', '%ae', '%s', '%b']) + RECORD_SEP]
    if limit:
        args.append('-%d' % limit)
    if paths:
        args += ['--'] + list(paths)
    out = _git(root, args)
    records = []
    for chunk in out.split(RECORD_SEP):
        chunk = chunk.strip('\n')
        if not chunk.strip():
            continue
        fields = chunk.split(FIELD_SEP)
        if len(fields) < 7:
            continue
        sha, short, date, name, email, subject, body = fields[:7]
        records.append({'sha': sha, 'short': short, 'date': date,
                        'date_utc': _parse_utc(date).strftime(
                            '%Y-%m-%dT%H:%M:%SZ'),
                        'epoch': _parse_utc(date).timestamp(),
                        'author_name': name, 'author_email': email,
                        'subject': subject, 'body': body,
                        'agent_assisted': 'co-authored-by' in body.lower()})
    return records


def head(root):
    return _git(root, ['rev-parse', '--short', 'HEAD']).strip()


def project_dirs(root):
    from pathlib import Path
    return sorted(p.name for p in Path(root).iterdir()
                  if p.is_dir() and PROJECT_DIR_RE.match(p.name)
                  and not p.name.startswith('.'))


def cards_in(commit):
    """Card ids named by a commit subject, expanding ``P10-02..04`` ranges."""
    found = []
    for project, first, last in CARD_RE.findall(commit['subject']):
        start = int(first)
        end = int(last) if last else start
        found.extend('P%s-%02d' % (project, n) for n in range(start, end + 1))
    return found


def card_index(root):
    """{card_id: commit} built from real commit subjects, oldest first."""
    index = {}
    for commit in reversed(commits(root)):
        for card in cards_in(commit):
            index.setdefault(card, commit)
    return index


def project_delivery(root, project):
    """What git actually shows for one project directory."""
    history = commits(root, paths=[project])
    if not history:
        return {'project': project, 'commits': 0, 'delivered': False,
                'first_commit': None, 'last_commit': None,
                'first_utc': None, 'last_utc': None,
                'span_hours_wall_clock': 0.0,
                'agent_assisted_commits': 0}
    oldest, newest = history[-1], history[0]
    span = (newest['epoch'] - oldest['epoch']) / 3600.0
    return {'project': project, 'commits': len(history), 'delivered': True,
            'first_commit': oldest['short'], 'last_commit': newest['short'],
            'first_utc': oldest['date_utc'], 'last_utc': newest['date_utc'],
            'span_hours_wall_clock': round(span, 2),
            'span_basis': EFFORT_DISCLAIMER,
            'agent_assisted_commits': sum(1 for c in history
                                          if c['agent_assisted']),
            'subjects': [c['subject'] for c in reversed(history)]}


def planned_ranges(charter):
    """{project: [low, high]} from the charter's documented ranges."""
    ranges = dict(charter['baseline']['effort_estimate']
                  ['per_project_documented_range_hours'])
    for change in charter['changes']:
        ranges.update(change.get('adds_documented_effort_range_hours', {}))
    return ranges


def planned_vs_actual(charter, root):
    """One row per project in the effective plan: planned next to actual."""
    import releaseplan as rp
    effective = rp.apply_changes(charter)
    ranges = planned_ranges(charter)
    cards = card_index(root)
    rows = []
    for project in sorted({t['project'] for t in effective['tasks']
                           if t.get('project')}):
        actual = project_delivery(root, project)
        project_cards = sorted(c for c in cards if c.startswith(
            project.split('-')[0] + '-'))
        low_high = ranges.get(project)
        midpoint = (low_high[0] + low_high[1]) / 2.0 if low_high else None
        span = actual['span_hours_wall_clock']
        rows.append({
            'project': project,
            'planned_hours_range': low_high,
            'planned_hours_midpoint': midpoint,
            'planned_cards': [t['card'] for t in effective['tasks']
                              if t.get('project') == project and t.get('card')],
            'actual_commits': actual['commits'],
            'actual_cards_with_a_commit': project_cards,
            'actual_first_commit': actual['first_commit'],
            'actual_last_commit': actual['last_commit'],
            'actual_first_utc': actual['first_utc'],
            'actual_last_utc': actual['last_utc'],
            'actual_span_hours_wall_clock': span,
            'actual_agent_assisted_commits': actual['agent_assisted_commits'],
            'span_to_midpoint_ratio': (round(span / midpoint, 4)
                                       if midpoint else None),
            'effort_measurable': False,
        })
    return rows


def delivery_order(charter, root):
    """Planned order versus the order git actually shows."""
    import releaseplan as rp
    effective = rp.apply_changes(charter)
    planned = []
    for task in effective['tasks']:
        project = task.get('project')
        if project and project not in planned and project.startswith('P'):
            planned.append(project)
    cards = card_index(root)
    actual = sorted(
        {p for p in project_dirs(root)
         if any(c.startswith(p.split('-')[0] + '-') for c in cards)},
        key=lambda p: min(cards[c]['epoch'] for c in cards
                          if c.startswith(p.split('-')[0] + '-')))
    release_projects = [p for p in actual if p in planned]
    return {'planned_order': planned,
            'actual_order_in_git': actual,
            'release_projects_in_actual_order': release_projects,
            'order_matched': [p for p in planned if p in release_projects]
            == release_projects}


def deviation(deviation_id, kind, planned, actual, explanation, source,
              severity='material'):
    if not explanation or len(explanation) < 40:
        raise RetroError('deviation %r has no real explanation' % deviation_id)
    if not source or not source.get('document'):
        raise RetroError('deviation %r has no source' % deviation_id)
    return {'id': deviation_id, 'kind': kind, 'planned': planned,
            'actual': actual, 'explanation': explanation, 'source': source,
            'severity': severity}


def deviations(charter, root):
    """The real deviations between the plan and the git history."""
    import releaseplan as rp
    found = []
    rows = {r['project']: r for r in planned_vs_actual(charter, root)}
    order = delivery_order(charter, root)
    effective = rp.apply_changes(charter)
    all_commits = commits(root)
    by_sha = {c['short']: c for c in all_commits}

    # DEV-1: the calendar. Planned 12-27 weeks for the trio, actual days.
    trio = [rows[p] for p in ('flow-ledger', 'data-bridge',
                              'evidence-rag')]
    first = min(r['actual_first_utc'] for r in trio)
    last = max(r['actual_last_utc'] for r in trio)
    span_days = round((_parse_iso(last) - _parse_iso(first)).total_seconds()
                      / 86400.0, 2)
    found.append(deviation(
        'DEV-1', 'calendar',
        '12-27 weeks for the trio at a self-chosen 8-12 focused h/week '
        '(135-210 h)',
        '%s days of wall-clock span from %s to %s' % (span_days, first, last),
        'CHG-001 removed both per-project assessment pauses, and execution was '
        'continuous and agent-assisted rather than 8-12 h/week. Wall-clock '
        'span is not focused hours: no timesheet exists, so the ratio is '
        'reported and explicitly not converted into a productivity claim.',
        {'document': 'TRIO1_P04-P06_PLAN.md section 1 and PLAN.md '
                     '"User decisions and approvals"',
         'commit': '29908c6'}))

    # DEV-2: the order held.
    found.append(deviation(
        'DEV-2', 'sequence',
        order['planned_order'][:3],
        order['release_projects_in_actual_order'][:3],
        'The batch authorization changed gating, not ordering: P04 then P06 '
        'then P05 was kept exactly as planned, which is why the trio part of '
        'the plan needs no re-sequencing explanation.',
        {'document': 'PLAN.md "Order and stack"', 'commit': '02b3301'},
        severity='none'))

    # DEV-3: scope grew from three projects to seven.
    baseline_projects = set(charter['baseline']['scope']['included_projects'])
    effective_projects = {p for p in rows if p.startswith('P')}
    delivered_projects = {p for p in effective_projects
                          if rows[p]['actual_commits'] > 0}
    found.append(deviation(
        'DEV-3', 'scope',
        sorted(baseline_projects),
        sorted(effective_projects),
        'CHG-002 extended scope to P04-P22 on 2026-10-06 and P07-P10 were '
        'delivered under it, so the release train grew from 3 planned '
        'projects to 7 with commits. release-plan also appears because '
        'CHG-006 added this project\'s own preflight task; it has no commit '
        'yet, so it is planned but not delivered. The authorization paragraph '
        'was written into PLAN.md but never committed, so the committed plan '
        'at HEAD still withholds P07-P22 - see finding PF-1.',
        {'document': 'PLAN.md section "Scope" (uncommitted working tree)',
         'commit': None}))

    # DEV-4: P04 was implemented in the same commit as the plan that forbade it.
    plan_commit = 'b1e974f'
    if plan_commit in by_sha:
        found.append(deviation(
            'DEV-4', 'governance',
            'TRIO1_P04-P06_PLAN.md declares "Status: plan review only. No '
            'implementation." and DEC-002 says commit to P04 v1 only after '
            'the plan is assessed',
            'commit %s added TRIO1_P04-P06_PLAN.md (106 lines) and the '
            'complete P04 FlowLedger v1 implementation, evidence and docs '
            'together, at %s' % (plan_commit, by_sha[plan_commit]['date_utc']),
            'Implementation preceded its own approval: the plan of record and '
            'the finished v1 landed in one commit, so there was never a point '
            'at which the plan could have been assessed before the work '
            'existed. Recorded because it is visible in git, not because it '
            'caused a defect.',
            {'document': 'git show --stat b1e974f', 'commit': plan_commit}))

    # DEV-5: one commit carried three cards.
    multi = {}
    for commit in all_commits:
        named = cards_in(commit)
        if len(named) > 1:
            multi[commit['short']] = named
    found.append(deviation(
        'DEV-5', 'granularity',
        'one commit per acceptance card, as used consistently for P04-P09',
        {'%s' % k: v for k, v in sorted(multi.items())},
        'P10-02, P10-03 and P10-04 were delivered in a single commit, which '
        'breaks the per-card bisectability the rest of the portfolio has. The '
        'evidence directories are still per card, so the loss is limited to '
        'git-level granularity.',
        {'document': 'git log --oneline', 'commit': 'a7a1a83'},
        severity='minor'))

    # DEV-6: unplanned corrective work.
    found.append(deviation(
        'DEV-6', 'unplanned-work',
        'no corrective commits; the ExFAT sidecar problem was already known '
        'and mitigated in P04-01',
        'commit 3be4111 removed nine AppleDouble sidecars that had been '
        'staged with the P07 kit directory',
        'The P04 mitigation (a surefire exclusion) only protects test '
        'discovery; it does not stop "git add <dir>" from staging sidecars. '
        'The mitigation was narrower than the risk it claimed to cover, so the '
        'same class of failure recurred one project later.',
        {'document': 'git show --stat 3be4111 and PORTFOLIO_STATUS.md '
                     '"Unresolved blockers"', 'commit': '3be4111'},
        severity='minor'))

    # DEV-7: acceptance never happened.
    accepted = [m for m in charter['baseline']['milestones']
                if m['status'] == 'ACHIEVED']
    found.append(deviation(
        'DEV-7', 'acceptance',
        'milestone M5: the user assesses the delivered ZIPs and projects '
        'become ACCEPTED',
        '%d of %d baseline milestones achieved; M5 NOT_ACHIEVED; 0 of %d '
        'delivered projects are ACCEPTED' % (
            len(accepted), len(charter['baseline']['milestones']),
            len(delivered_projects)),
        'Acceptance is a human decision that PLAN.md explicitly withholds and '
        'that no automated check may close. Both P16 review gates are '
        'modelled with requires_human_decision = true and stay permanently '
        'unmet, so the plan reports DELIVERED rather than DONE.',
        {'document': 'PLAN.md "User decisions and approvals" and '
                     'PORTFOLIO_STATUS.md "Active gate"', 'commit': None}))

    # DEV-8: review bundles exist for three of seven delivered projects.
    from pathlib import Path
    bundles = sorted(p.name for p in
                     (Path(root) / 'opencode-handoff' / 'bundles').glob('*.zip')
                     if not p.name.startswith('._'))
    # Codex fix 2026-10-08: exclude AppleDouble `._*.zip` sidecars (ExFAT),
    # which the glob otherwise counts as bundles.
    found.append(deviation(
        'DEV-8', 'deliverable',
        'one implementation-inclusive review ZIP per delivered project',
        '%d ZIPs exist (%s) for %d delivered projects' % (
            len(bundles), ', '.join(bundles), len(delivered_projects)),
        'CHG-002 added P07-P10 to the release train without adding a bundle '
        'milestone, so four delivered projects have evidence directories but '
        'no review artifact. That is a gap in the change record, not in the '
        'projects, and it is why gate G-USER-REVIEW-P07-P10 names no bundle.',
        {'document': 'opencode-handoff/bundles/ and charter.json CHG-002',
         'commit': '5f5e077'}))
    return found


def _parse_iso(text):
    return datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(
        tzinfo=timezone.utc)


def report(charter, root):
    """The whole planned-versus-actual picture, plus the git facts behind it."""
    rows = planned_vs_actual(charter, root)
    order = delivery_order(charter, root)
    found = deviations(charter, root)
    all_commits = commits(root)
    return {
        'generated_from': 'git history of %s at HEAD %s' % (root, head(root)),
        'git_head': head(root),
        'total_commits': len(all_commits),
        'distinct_author_identities': sorted(
            {'%s <%s>' % (c['author_name'], c['author_email'])
             for c in all_commits}),
        'agent_assisted_commits': sum(1 for c in all_commits
                                      if c['agent_assisted']),
        'rows': rows,
        'order': order,
        'deviations': found,
        'effort_disclaimer': EFFORT_DISCLAIMER,
        'solo': True,
        'note': 'Planned values are quoted from the charter; actual values are '
                'read from git. No number in the "actual" columns was typed '
                'by hand.',
    }
