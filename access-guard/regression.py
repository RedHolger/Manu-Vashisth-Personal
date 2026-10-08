"""CI regression runner for AccessGuard (P11-03): before/after with one oracle.

`RegressionRunner.before_after()` drives the FULL extended matrix against a
seeded (vulnerable) target and a repaired (fixed) target using the SAME
unaltered oracle. It re-hashes `policy_oracle.py` around every run and
refuses to report if the oracle moved — the oracle is never adjusted to make
a target pass. Both reports are retained; the gate is PASS only when the
repaired target is clean AND the seeded target still shows its findings
(a gate that cannot fail is not a gate).

`TargetAdapter.probe()` checks the concrete prerequisites for the v1.1 live
FlowLedger/EvidenceRAG integration (reachable Docker daemon, PostgreSQL on
loopback, a DB driver). When anything is missing it reports BLOCKED and
`provision()` raises `IntegrationBlocked` — it never hands back a stand-in
or simulates a live result.
"""
import hashlib
import json
import shutil
import socket
import subprocess
from pathlib import Path

import lab_app
import runner

ORACLE_PATH = Path(__file__).parent / 'policy_oracle.py'


def oracle_sha256():
    return hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest()


class OracleMovedError(RuntimeError):
    """The oracle changed mid-run; the comparison is void."""


class IntegrationBlocked(RuntimeError):
    """Live-target prerequisites are missing; no stand-in is provided."""


class RegressionRunner:
    """Before/after gate over the full extended matrix."""

    def __init__(self, which='extended'):
        self.which = which
        self.oracle_before = oracle_sha256()

    def _guard_oracle(self):
        if oracle_sha256() != self.oracle_before:
            raise OracleMovedError(
                'policy_oracle.py changed during the run; refusing to gate')

    def run_target(self, bugs, label):
        self._guard_oracle()
        report = runner.evaluate(bugs, self.which)
        self._guard_oracle()
        report['target_label'] = label
        return report

    def before_after(self):
        """(before, after, gate). Gate PASS needs a clean repair AND a
        still-failing seeded target."""
        before = self.run_target(lab_app.VULNERABLE_BUGS, 'seeded')
        after = self.run_target(frozenset(), 'repaired')
        seeded_fails = before['mismatches'] > 0
        repaired_clean = after['mismatches'] == 0
        gate = 'PASS' if (seeded_fails and repaired_clean) else 'FAIL'
        return {'before': before, 'after': after, 'gate': gate,
                'oracle_sha256': self.oracle_before,
                'oracle_unchanged': True}

    @staticmethod
    def gate_for(report):
        """Standalone gate for one report (used to prove the gate can fail)."""
        return 'FAIL' if report['mismatches'] > 0 else 'PASS'


class TargetAdapter:
    """Prerequisite probe for the v1.1 live FlowLedger/EvidenceRAG targets."""

    LIVE_TARGETS = ('flow-ledger', 'evidence-rag')

    @staticmethod
    def _docker_reachable():
        if shutil.which('docker') is None:
            return False, 'no docker binary'
        try:
            proc = subprocess.run(['docker', 'info'], capture_output=True,
                                  timeout=15)
        except Exception as exc:
            return False, 'docker info error: %s' % type(exc).__name__
        return (True, 'ok') if proc.returncode == 0 else (
            False, 'docker info exit %d' % proc.returncode)

    @staticmethod
    def _pg_reachable(port):
        try:
            sock = socket.create_connection(('127.0.0.1', port), timeout=3)
            sock.close()
            return True
        except OSError:
            return False

    @staticmethod
    def _driver_available():
        try:
            import psycopg  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def probe(cls):
        """Report READY/BLOCKED per live target with concrete prerequisites."""
        docker_ok, docker_note = cls._docker_reachable()
        pg = {port: cls._pg_reachable(port) for port in (5433, 5434, 5435)}
        driver = cls._driver_available()
        results = {}
        for target in cls.LIVE_TARGETS:
            missing = []
            if not docker_ok:
                missing.append('docker daemon unreachable (%s)' % docker_note)
            if not any(pg.values()):
                missing.append('no PostgreSQL on 127.0.0.1:5433/5434/5435')
            if not driver:
                missing.append('no psycopg driver in system python')
            results[target] = {'status': 'READY' if not missing else 'BLOCKED',
                               'missing': missing,
                               'observed': {'docker': docker_ok,
                                            'pg_ports': pg,
                                            'driver': driver}}
        return results

    @classmethod
    def provision(cls, target):
        """Return a live adapter, or raise instead of substituting."""
        status = cls.probe()[target]['status']
        if status != 'READY':
            raise IntegrationBlocked(
                '%s live integration BLOCKED; refusing a stand-in '
                '(see probe())' % target)
        raise IntegrationBlocked(
            '%s probe passed but no live adapter is implemented in this '
            'card; refusing to invent one' % target)


def no_credentials(blob):
    """True when a serialized report carries no bearer value."""
    return 'tok-' not in (blob if isinstance(blob, str) else json.dumps(blob))
