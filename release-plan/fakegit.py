"""Stubbed git layer for preflight tests and measurements.

No git write command is used anywhere: these fixtures fake ``preflight``'s git
calls so the checker can be proven capable of returning OK / exit 0 without
creating a repository. Real-repository assertions run the actual read-only git
plumbing instead.
"""
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import preflight


class Completed:
    def __init__(self, stdout='', returncode=0, stderr=''):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class FakeRepo:
    """Canned git behaviour for a synthetic repository."""

    def __init__(self, root):
        self.root = Path(root)
        self.head = 'aaaaaaa'
        self.head_date = '2026-10-08T12:00:00+00:00'
        self.committed_files = {}      # path -> committed text
        self.working_files = {}        # path -> working tree text
        self.tracked = []              # git ls-files
        self.status = []               # git status --porcelain lines
        self.project_commits = {}      # dir -> commit count
        self.doc_commits = {}          # doc -> (sha, date)
        self.commits_since = {}        # (sha, path|None) -> count

    def git(self, root, args):
        if args[0] == 'show' and args[1].startswith('HEAD:'):
            path = args[1].split(':', 1)[1]
            if path in self.committed_files:
                return Completed(self.committed_files[path])
            return Completed('', 128, "fatal: path '%s' does not exist" % path)
        if args[0] == 'log' and '-1' in args:
            doc = args[-1] if args[-2] == '--' else None
            if doc is None:
                return Completed(self.head_date + '\n')
            if doc in self.doc_commits:
                sha, date = self.doc_commits[doc]
                fmt = next(a for a in args if a.startswith('--format'))
                if '%x1f' in fmt:
                    return Completed(sha + '\x1f' + date + '\n')
                return Completed(date + '\n')
            return Completed('', 0)
        if args[0] == 'diff' and '--quiet' in args:
            doc = args[-1]
            same = self.committed_files.get(doc) == self.working_files.get(doc)
            return Completed('', 0 if same else 1)
        if args[0] == 'rev-parse':
            return Completed(self.head + '\n')
        raise AssertionError('unexpected git call %r' % (args,))

    def git_out(self, root, args):
        result = self.git(root, args) if args[0] in (
            'show', 'log', 'rev-parse') else None
        if result is not None:
            if result.returncode != 0:
                raise preflight.PreflightError(result.stderr)
            return result.stdout
        if args[:2] == ['rev-list', '--count']:
            if 'HEAD' in args:
                name = args[-1]
                return '%d\n' % self.project_commits.get(name, 0)
            key = (args[2].split('..')[0], args[-1] if args[-2] == '--'
                   else None)
            return '%d\n' % self.commits_since.get(key, 0)
        if args[0] == 'ls-files':
            return '\n'.join(self.tracked) + ('\n' if self.tracked else '')
        if args[:2] == ['status', '--porcelain']:
            return '\n'.join(self.status) + ('\n' if self.status else '')
        raise AssertionError('unexpected git call %r' % (args,))


def clean_repo(tmp):
    """A synthetic repository with no drift at all."""
    root = Path(tmp)
    (root / '.git').mkdir(exist_ok=True)
    (root / 'P90-demo').mkdir(exist_ok=True)
    plan = ('# Plan\n\n## User decisions and approvals\n\n- Authorized: '
            'P90.\n- Not authorized and still withheld: pushing to a '
            'remote.\n')
    status = ('# Status\n\nP90-demo is delivered. Last inspected: '
              '2026-10-08T12:00:00Z\n')
    repo = FakeRepo(root)
    repo.committed_files = {'PLAN.md': plan, 'PORTFOLIO_STATUS.md': status,
                            'HANDOFF.md': status}
    repo.working_files = dict(repo.committed_files)
    for name, text in repo.working_files.items():
        (root / name).write_text(text, encoding='utf-8')
    repo.tracked = ['PLAN.md', 'PORTFOLIO_STATUS.md', 'HANDOFF.md',
                    'P90-demo/project.py']
    repo.project_commits = {'P90-demo': 3}
    repo.doc_commits = {'PORTFOLIO_STATUS.md': ('bbbbbbb',
                                                '2026-10-08T12:00:00+00:00'),
                        'HANDOFF.md': ('bbbbbbb', '2026-10-08T12:00:00+00:00')}
    repo.commits_since = {('bbbbbbb', 'P90-demo'): 0, ('bbbbbbb', None): 0}
    return repo


def set_working(repo, name, text):
    """Change the working-tree copy the way an uncommitted edit would."""
    repo.working_files[name] = text
    (repo.root / name).write_text(text, encoding='utf-8')


def set_committed(repo, name, text):
    """Change what 'git show HEAD:<name>' returns, keeping the tree in sync."""
    repo.committed_files[name] = text
    set_working(repo, name, text)


def patched_run(repo):
    """Run preflight against a FakeRepo without touching real git."""
    with mock.patch.object(preflight, '_git', side_effect=repo.git), \
            mock.patch.object(preflight, '_git_out',
                              side_effect=repo.git_out):
        return preflight.run(repo.root)


def temp_root(prefix='p16-preflight-'):
    """A throwaway directory; the caller is responsible for removing it."""
    return Path(tempfile.mkdtemp(prefix=prefix))
