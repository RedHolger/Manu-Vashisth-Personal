"""preflight.py - the P16-04 process fix for a demonstrated planning failure.

The failure this exists for is real and reproducible in this repository:

* **PF-1 authorization of record drift.** ``PLAN.md`` was edited to authorize
  "P04-P22", but the edit was never committed. ``git show HEAD:PLAN.md`` still
  reads *"Not authorized and still withheld: ... starting P07-P22"* while 17
  commits deliver P07-P10. The authorization that git records and the work git
  records contradict each other.
* **PF-2 stale root status documents.** ``PORTFOLIO_STATUS.md`` and
  ``HANDOFF.md`` were last committed at ``f4996a8`` (2026-10-06T21:34:32Z) and
  mention P07/P08/P09/P10 **zero** times, while commits through ``a7a1a83``
  (2026-10-08T17:57:28Z) delivered all four.
* **PF-3 tracked build artifacts.** 54 files under ``flow-ledger/target/``
  are tracked, so the working tree can never be clean.
* **PF-4 AppleDouble noise.** The ExFAT volume regenerates ``._*`` sidecars;
  nine of them already reached a commit once (``3be4111``).
* **PF-5 evidence-directory contract.** Some ``results/<run-id>/`` directories
  predate the ``command.txt`` convention.

This script is **read-only**. It runs git plumbing commands and reads files; it
writes nothing except its own ``--out`` report. Where a fix belongs outside
``release-plan/`` it emits a precise ``recommendation`` and marks
``owner_scope: outside-p16`` instead of applying it.

Usage::

    python3 -B preflight.py                 # human summary, exit 1 on any FAIL
    python3 -B preflight.py --json          # machine-readable report
    python3 -B preflight.py --out DIR       # also write preflight-report.json

Exit 0 means no FAIL finding. On this repository it exits 1, which is the
correct result: the planning failure is still present at the root and P16 is
not allowed to edit it.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
PLAN_DOC = 'PLAN.md'
STATUS_DOCS = ('PORTFOLIO_STATUS.md', 'HANDOFF.md')
BUILD_PATTERNS = ('target/', 'node_modules/', '__pycache__/', '.venv/',
                  'dist/', 'build/', '.pytest_cache/')
PROJECT_DIR_RE = re.compile(r'^P(\d{2})-')
WITHHELD_RE = re.compile(r'[Nn]ot authorized and still withheld[^\n]*')
PROJECT_RANGE_RE = re.compile(r'P(\d{2})\s*[\u2013\u2014-]\s*P(\d{2})')
SINGLE_PROJECT_RE = re.compile(r'\bP(\d{2})\b')

SEVERITY_OK, SEVERITY_WARN, SEVERITY_FAIL = 'OK', 'WARN', 'FAIL'


class PreflightError(RuntimeError):
    """Raised when the repository cannot be inspected at all."""


def _git(root, args, timeout=120):
    result = subprocess.run(['git', '-C', str(root)] + args,
                            capture_output=True, text=True, timeout=timeout)
    return result


def _git_out(root, args):
    result = _git(root, args)
    if result.returncode != 0:
        raise PreflightError('git %s failed: %s'
                             % (args, result.stderr.strip()))
    return result.stdout


def _utc(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def finding(check_id, check, severity, summary, evidence, recommendation,
            owner_scope):
    return {'id': check_id, 'check': check, 'severity': severity,
            'summary': summary, 'evidence': evidence,
            'recommendation': recommendation, 'owner_scope': owner_scope}


def delivered_projects(root):
    """{project_dir: number} for every root project dir that has commits."""
    out = {}
    for path in sorted(Path(root).iterdir()):
        match = PROJECT_DIR_RE.match(path.name)
        if not match or not path.is_dir():
            continue
        count = _git_out(root, ['rev-list', '--count', 'HEAD', '--',
                                path.name]).strip()
        if count and int(count) > 0:
            out[path.name] = int(match.group(1))
    return out


def withheld_project_numbers(text):
    """Project numbers the *given* plan text says are not authorized."""
    withheld = set()
    for line in WITHHELD_RE.findall(text):
        for low, high in PROJECT_RANGE_RE.findall(line):
            withheld.update(range(int(low), int(high) + 1))
        for single in SINGLE_PROJECT_RE.findall(line):
            withheld.add(int(single))
    return sorted(withheld)


def pf1_authorization_of_record(root):
    """Delivered work must be authorized by the plan git actually records."""
    committed = _git(root, ['show', 'HEAD:%s' % PLAN_DOC])
    if committed.returncode != 0:
        return finding('PF-1', 'authorization-of-record', SEVERITY_FAIL,
                       'no committed %s at HEAD; there is no authorization of '
                       'record at all' % PLAN_DOC,
                       {'command': 'git show HEAD:%s' % PLAN_DOC},
                       'Commit the plan document.', 'outside-p16')
    committed_text = committed.stdout
    working_text = (Path(root) / PLAN_DOC).read_text(encoding='utf-8')
    withheld_committed = withheld_project_numbers(committed_text)
    withheld_working = withheld_project_numbers(working_text)
    delivered = delivered_projects(root)

    drift = sorted(name for name, number in delivered.items()
                   if number in withheld_committed)
    uncommitted_authorization = committed_text != working_text
    evidence = {
        'committed_withholds_project_numbers': withheld_committed,
        'working_tree_withholds_project_numbers': withheld_working,
        'delivered_projects': {k: v for k, v in sorted(delivered.items())},
        'delivered_but_withheld_at_HEAD': drift,
        'plan_working_tree_differs_from_HEAD': uncommitted_authorization,
        'commands': ['git show HEAD:%s' % PLAN_DOC,
                     'git diff -- %s' % PLAN_DOC,
                     'git rev-list --count HEAD -- <project-dir>'],
    }
    if drift:
        return finding(
            'PF-1', 'authorization-of-record', SEVERITY_FAIL,
            '%d delivered project(s) are still withheld by the committed plan '
            'of record: %s' % (len(drift), ', '.join(drift)),
            evidence,
            'Commit the %s scope paragraph that authorizes them, or amend the '
            'withholding clause so the committed record matches the delivered '
            'work. Both files are outside release-plan/ and were not '
            'modified.' % PLAN_DOC, 'outside-p16')
    if uncommitted_authorization:
        return finding(
            'PF-1', 'authorization-of-record', SEVERITY_WARN,
            '%s in the working tree differs from HEAD; an authorization that '
            'is not committed is not the authorization of record' % PLAN_DOC,
            evidence, 'Commit %s.' % PLAN_DOC, 'outside-p16')
    return finding('PF-1', 'authorization-of-record', SEVERITY_OK,
                   'every delivered project is authorized by the committed '
                   'plan of record', evidence, 'none', 'outside-p16')


def pf2_doc_freshness(root, docs=STATUS_DOCS):
    """A status document must not lag the work it claims to describe."""
    delivered = delivered_projects(root)
    stale, details = [], {}
    for doc in docs:
        path = Path(root) / doc
        if not path.exists():
            stale.append(doc)
            details[doc] = {'exists': False}
            continue
        log = _git(root, ['log', '-1', '--format=%H%x1f%aI', '--', doc])
        text = path.read_text(encoding='utf-8')
        if log.returncode != 0 or not log.stdout.strip():
            details[doc] = {'exists': True, 'committed': False,
                            'unmentioned_projects': sorted(delivered)}
            stale.append(doc)
            continue
        sha, date = log.stdout.strip().split('\x1f')
        epoch = _utc(date).timestamp()
        unmentioned, newer, mentions_by_project = [], [], {}
        for name, number in sorted(delivered.items()):
            tag = 'P%02d' % number
            mentions = len(re.findall(r'\b%s\b' % tag, text))
            after = _git_out(root, ['rev-list', '--count', '%s..HEAD' % sha,
                                    '--', name]).strip()
            mentions_by_project[name] = mentions
            if mentions == 0:
                unmentioned.append(name)
            if int(after) > 0:
                newer.append({'project': name, 'commits_after_doc': int(after)})
        lag_commits = int(_git_out(root, ['rev-list', '--count',
                                          '%s..HEAD' % sha]).strip())
        head_date = _utc(_git_out(root, ['log', '-1', '--format=%aI']).strip())
        details[doc] = {
            'exists': True, 'committed': True, 'last_commit': sha[:7],
            'last_commit_utc': _utc(date).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'head_utc': head_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'lag_hours': round((head_date.timestamp() - epoch) / 3600.0, 1),
            'commits_since_doc': lag_commits,
            'projects_with_commits_after_doc': newer,
            'delivered_projects_not_mentioned': unmentioned,
            'mention_counts': mentions_by_project,
            'mention_caveat': 'a mention is counted anywhere in the document, '
                              'including inside a "not authorized" clause; a '
                              'low count with commits after the document is '
                              'the staleness signal',
            'working_tree_modified': bool(
                _git(root, ['diff', '--quiet', '--', doc]).returncode != 0),
        }
        if unmentioned and newer:
            stale.append(doc)
    severity = SEVERITY_FAIL if stale else SEVERITY_OK
    return finding(
        'PF-2', 'doc-freshness', severity,
        ('%s lag the delivered work: %s' % (
            ' and '.join(docs), ', '.join(stale))) if stale else
        'every status document mentions every delivered project',
        details,
        'Re-inspect and re-commit %s whenever a project directory gains a '
        'commit, and run this checker before each commit. Root adoption is a '
        'recommendation: these documents are outside release-plan/ and '
        'were not modified.' % ' and '.join(docs),
        'outside-p16')


def pf3_tracked_build_artifacts(root):
    tracked = _git_out(root, ['ls-files']).splitlines()
    hits = sorted(p for p in tracked
                  if any(('/' + pat) in ('/' + p) or p.startswith(pat)
                         for pat in BUILD_PATTERNS))
    by_dir = {}
    for path in hits:
        by_dir[path.split('/')[0]] = by_dir.get(path.split('/')[0], 0) + 1
    severity = SEVERITY_FAIL if hits else SEVERITY_OK
    return finding(
        'PF-3', 'tracked-build-artifacts', severity,
        '%d tracked build artifact(s)%s' % (
            len(hits), ' under ' + ', '.join(sorted(by_dir)) if by_dir else ''),
        {'count': len(hits), 'by_top_level_dir': by_dir,
         'patterns': list(BUILD_PATTERNS),
         'sample': hits[:10],
         'command': "git ls-files | grep -E '(^|/)(%s)'"
                    % '|'.join(p.rstrip('/') for p in BUILD_PATTERNS)},
        'Add the build directories to .gitignore and run '
        "'git rm -r --cached <dir>' in a dedicated commit. Both are outside "
        'release-plan/ and were not run here.', 'outside-p16')


def pf4_appledouble_noise(root):
    porcelain = _git_out(root, ['status', '--porcelain']).splitlines()
    sidecars = [line for line in porcelain
                if Path(line[3:].strip().strip('"')).name.startswith('._')]
    tracked_sidecars = [p for p in _git_out(root, ['ls-files']).splitlines()
                        if Path(p).name.startswith('._')]
    staged = [line for line in sidecars if line[:2].strip()
              and not line.startswith('??')]
    severity = (SEVERITY_FAIL if tracked_sidecars or staged
                else (SEVERITY_WARN if sidecars else SEVERITY_OK))
    return finding(
        'PF-4', 'appledouble-noise', severity,
        '%d AppleDouble sidecar(s) in git status, %d tracked, %d staged'
        % (len(sidecars), len(tracked_sidecars), len(staged)),
        {'in_status': len(sidecars), 'tracked': len(tracked_sidecars),
         'staged': len(staged),
         'cause': 'the workspace volume is ExFAT, so macOS regenerates ._* '
                  'metadata siblings; nine of them reached commit 3be4111',
         'commands': ["git status --porcelain", "git ls-files"]},
        'Never "git add -A" on this volume; stage explicit paths. Add ._* to '
        'a global gitignore. Root-level configuration is outside '
        'release-plan/ and was not changed.', 'outside-p16')


def pf5_results_dir_contract(root):
    missing = []
    total = 0
    for project in sorted(delivered_projects(root)):
        results = Path(root) / project / 'results'
        if not results.is_dir():
            continue
        for run in sorted(p for p in results.iterdir() if p.is_dir()):
            total += 1
            if not (run / 'command.txt').exists():
                missing.append('%s/%s' % (project, run.name))
    severity = SEVERITY_WARN if missing else SEVERITY_OK
    return finding(
        'PF-5', 'results-dir-contract', severity,
        '%d of %d results directories have no command.txt' % (
            len(missing), total),
        {'total_results_dirs': total, 'missing_command_txt': missing,
         'convention': "PLAN.md 'Local-only and evidence rules': every run "
                       'gets a unique results/<run-id>/ with the exact '
                       'command and exit code'},
        'Backfill command.txt for historical runs, or record in the project '
        'HANDOFF.md that they predate the convention. Those directories are '
        'outside release-plan/ and were not modified.', 'outside-p16')


CHECKS = (pf1_authorization_of_record, pf2_doc_freshness,
          pf3_tracked_build_artifacts, pf4_appledouble_noise,
          pf5_results_dir_contract)


def run(root=None, as_of=None):
    root = Path(root or DEFAULT_ROOT)
    if not (root / '.git').exists():
        raise PreflightError('%s is not a git repository' % root)
    findings = [check(root) for check in CHECKS]
    counts = {sev: sum(1 for f in findings if f['severity'] == sev)
              for sev in (SEVERITY_OK, SEVERITY_WARN, SEVERITY_FAIL)}
    return {
        'tool': 'preflight.py',
        'purpose': 'P16-04 process fix: fail a release whose planning record '
                   'has drifted from the work it describes',
        'generated_at': as_of or time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                               time.gmtime()),
        'root': str(root),
        'git_head': _git_out(root, ['rev-parse', '--short', 'HEAD']).strip(),
        'read_only': True,
        'findings': findings,
        'counts': counts,
        'exit_code': 1 if counts[SEVERITY_FAIL] else 0,
    }


def render(report):
    lines = ['preflight %s  root=%s  head=%s' % (
        report['generated_at'], report['root'], report['git_head'])]
    for item in report['findings']:
        lines.append('[%-4s] %-5s %-26s %s' % (
            item['severity'], item['id'], item['check'], item['summary']))
        if item['severity'] != SEVERITY_OK:
            lines.append('         recommendation (%s): %s'
                         % (item['owner_scope'], item['recommendation']))
    lines.append('counts: %s' % json.dumps(report['counts'], sort_keys=True))
    lines.append('exit_code: %d' % report['exit_code'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(DEFAULT_ROOT))
    parser.add_argument('--json', action='store_true',
                        help='print the machine-readable report')
    parser.add_argument('--out', help='write preflight-report.json here')
    options = parser.parse_args(argv)
    report = run(options.root)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text if options.json else render(report))
    if options.out:
        out = Path(options.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'preflight-report.json').write_text(text + '\n')
    return report['exit_code']


if __name__ == '__main__':
    sys.exit(main())
