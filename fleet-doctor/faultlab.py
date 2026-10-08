"""Disposable fault lab for FleetDoctor (P18-02): bounded, owned, cleaned.

Everything happens inside a lab root confined to the system temp dir (or a
project-local `tmp/`). `provision()` REFUSES `/`, `$HOME`, or any path
escaping the allowed roots — university/shared infrastructure can never be a
lab. Faults target only owned files and child processes, are time-bounded,
and `cleanup()` reaps processes, removes files and verifies the root is gone
(emergency stop = call `cleanup()`; it kills tracked PIDs first).

Docker/VMs are NOT used here (daemon unreachable); faults are process- and
dir-level and labeled as such — never as container/VM evidence. No spare
physical machine exists (see P18-04).
"""
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import checks


class LabRefused(RuntimeError):
    pass


def _allowed_roots():
    roots = [Path(tempfile.gettempdir()).resolve()]
    for cand in ('/tmp', '/var/tmp'):
        try:
            roots.append(Path(cand).resolve())
        except OSError:
            pass
    local = (Path(__file__).parent / 'tmp').resolve()
    roots.append(local)
    return roots


def _confined(path):
    resolved = Path(path).resolve()
    if resolved == Path('/').resolve() or resolved == Path.home().resolve():
        return False
    return any(resolved == r or r in resolved.parents for r in
               _allowed_roots())


class Lab:
    """One disposable lab: root dir + tracked child processes + files."""

    def __init__(self, name):
        self.name = name
        self.root = Path(tempfile.mkdtemp(prefix='fleetdoctor-%s-' % name))
        if not _confined(self.root):
            raise LabRefused('lab root %s not confined' % self.root)
        self.procs = []    # tracked subprocess.Popen objects
        self.files = []    # created files (for the manifest)
        self.faults = []   # seeded fault records
        self.cleaned = False

    @staticmethod
    def refuse(path):
        """True when `path` must never become a lab (guard for callers)."""
        return not _confined(path)

    # -- fault seeders (each verifies its own setup) --
    def seed_disk_exhaustion(self, fill_bytes=5_000_000, cap_bytes=1_000_000):
        blob = self.root / 'quota-hog.bin'
        blob.write_bytes(b'\0' * fill_bytes)
        self.files.append(str(blob))
        quota = checks.disk_quota(str(self.root), cap_bytes)
        if quota['status'] != 'FAIL':
            raise RuntimeError('disk-exhaustion setup did not trip the check')
        self.faults.append({'fault': 'disk-exhaustion', 'cap_bytes': cap_bytes,
                            'bytes_used': quota['bytes_used']})
        return quota

    def seed_killed_service(self):
        proc = subprocess.Popen(['sleep', '300'])
        self.procs.append(proc)
        time.sleep(0.2)
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=10)
        state = checks.process(pid=proc.pid)
        if state['status'] != 'FAIL':
            raise RuntimeError('killed-service setup did not read dead')
        self.faults.append({'fault': 'killed-service', 'pid': proc.pid})
        return state

    def seed_dns_failure(self):
        state = checks.dns('no-such-host.invalid')
        if state['status'] != 'FAIL':
            raise RuntimeError('dns-failure setup did not read failed')
        self.faults.append({'fault': 'dns-failure'})
        return state

    def seed_cpu_pressure(self, seconds=3, workers=2):
        burners = []
        for _ in range(workers):
            p = subprocess.Popen(
                ['python3', '-c', 'import time\nend=time.time()+%d\n'
                 'while time.time()<end:\n pass' % (seconds + 5)])
            burners.append(p)
            self.procs.append(p)
        time.sleep(min(seconds, 3))
        load = checks.load()
        for p in burners:
            p.terminate()
        for p in burners:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=10)
        self.procs = [p for p in self.procs if p not in burners]
        self.faults.append({'fault': 'cpu-pressure', 'seconds': seconds,
                            'workers': workers,
                            'load_observed': load.get('load_1_5_15')})
        return load

    # -- cleanup (emergency stop) --
    def cleanup(self):
        """Kill tracked processes, remove files/root, verify. Returns report."""
        killed, reaped = [], []
        for proc in list(self.procs):
            try:
                proc.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                proc.wait(timeout=10)
                reaped.append(proc.pid)
            except (subprocess.TimeoutExpired, OSError):
                killed.append(proc.pid)
        self.procs = []
        stray = []
        root_gone = False
        try:
            shutil.rmtree(self.root, ignore_errors=False)
            root_gone = not self.root.exists()
        except OSError:
            root_gone = not self.root.exists()
        self.cleaned = root_gone and not killed and not stray
        return {'root': str(self.root), 'root_removed': root_gone,
                'reaped_pids': reaped, 'unkilled_pids': killed,
                'stray': stray, 'cleaned': self.cleaned,
                'faults_seeded': [f['fault'] for f in self.faults]}

    def manifest(self):
        return {'lab': self.name, 'root': str(self.root),
                'confined': _confined(self.root),
                'faults': list(self.faults), 'files': list(self.files),
                'tracked_pids': [p.pid for p in self.procs]}
