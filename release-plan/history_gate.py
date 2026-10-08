"""Skip live-history tests outside the full-history workspace.

Some release-plan tests validate against the real R1 release history (live
git log, charter pins, bundle manifests). In a shallow/exported checkout
those inputs do not exist, so the tests skip with an explicit reason instead
of failing. Unit tests (fakegit, synthetic fixtures) always run.
"""
import subprocess


def has_full_history(root='.'):
    try:
        proc = subprocess.run(['git', '-C', str(root), 'rev-list',
                               '--count', 'HEAD'], capture_output=True,
                              text=True, timeout=30)
    except Exception:
        return False
    try:
        return int((proc.stdout or '0').strip()) >= 10
    except ValueError:
        return False


def require_full_history(root='.'):
    import unittest
    if not has_full_history(root):
        raise unittest.SkipTest(
            'needs full-history workspace with the R1 release history')
