"""Diagnostic plugins for FleetDoctor (P18-01): PASS/WARN/FAIL/UNKNOWN.

Every plugin returns `{status, evidence}`. The load-bearing rule: missing
permission or a missing tool yields UNKNOWN — never a healthy status. DNS
uses offline-safe names (`localhost` resolves, `.invalid` must not), so no
network dependence is assumed.
"""
import os
import shutil
import socket
import subprocess

import project

STATUSES = ('PASS', 'WARN', 'FAIL', 'UNKNOWN')


def disk(path='.'):
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return {'status': 'UNKNOWN', 'reason': type(exc).__name__,
                'path': str(path)}
    return {'status': project.classify_free(usage.total, usage.free),
            'total_bytes': usage.total, 'free_bytes': usage.free,
            'path': str(path)}


def _system_memory():
    """(total, free) bytes or None when unobtainable (→ UNKNOWN)."""
    try:
        with open('/proc/meminfo', encoding='utf-8') as handle:
            info = {}
            for line in handle:
                parts = line.split()
                if len(parts) >= 2 and parts[0].endswith(':'):
                    info[parts[0][:-1]] = int(parts[1]) * 1024
            if 'MemTotal' in info and 'MemAvailable' in info:
                return info['MemTotal'], info['MemAvailable']
    except OSError:
        pass
    try:
        proc = subprocess.run(['vm_stat'], capture_output=True, text=True,
                              timeout=5)
        if proc.returncode == 0:
            import re
            pages = {}
            for line in proc.stdout.splitlines():
                match = re.match(r'(.*):\s+(\d+)\.', line)
                if match:
                    pages[match.group(1).strip()] = int(match.group(2))
            page = 16384
            free = pages.get('Pages free', 0) * page
            total = sum(pages.get(k, 0) for k in pages) * page
            if total > 0:
                return total, free
    except (OSError, ValueError):
        pass
    return None


def memory():
    import resource
    own_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    sysmem = _system_memory()
    if sysmem is None:
        return {'status': 'UNKNOWN', 'reason': 'system memory unobtainable',
                'own_maxrss': own_rss}
    total, free = sysmem
    return {'status': project.classify_free(total, free),
            'total_bytes': total, 'free_bytes': free, 'own_maxrss': own_rss}


def dns(name='localhost'):
    try:
        ip = socket.gethostbyname(name)
    except socket.gaierror as exc:
        return {'status': 'FAIL', 'reason': 'resolution failure',
                'name': name, 'detail': str(exc)}
    except OSError as exc:
        return {'status': 'UNKNOWN', 'reason': type(exc).__name__,
                'name': name}
    return {'status': 'PASS', 'name': name, 'resolved': ip}


def process(pid=None, name=None):
    """Liveness of an owned PID (kill 0) or a named process (pgrep/ps)."""
    if pid is not None:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return {'status': 'FAIL', 'reason': 'no such process',
                    'pid': pid}
        except PermissionError:
            return {'status': 'UNKNOWN',
                    'reason': 'no permission to signal pid', 'pid': pid}
        except OSError as exc:
            return {'status': 'UNKNOWN', 'reason': type(exc).__name__,
                    'pid': pid}
        return {'status': 'PASS', 'pid': pid, 'alive': True}
    if name is not None:
        for argv in (['pgrep', '-x', name], ['ps', '-A', '-o', 'comm=']):
            try:
                proc = subprocess.run(argv, capture_output=True, text=True,
                                      timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if proc.returncode == 0 and name in proc.stdout:
                return {'status': 'PASS', 'name': name, 'found': True}
            if proc.returncode in (0, 1):
                return {'status': 'FAIL', 'reason': 'not running',
                        'name': name}
        return {'status': 'UNKNOWN', 'reason': 'no usable process tool',
                'name': name}
    raise ValueError('process() needs pid= or name=')


def load():
    try:
        avg = os.getloadavg()
    except OSError as exc:
        return {'status': 'UNKNOWN', 'reason': type(exc).__name__}
    cpus = os.cpu_count() or 1
    status = 'WARN' if avg[0] > cpus else 'PASS'
    return {'status': status, 'load_1_5_15': list(avg), 'cpu_count': cpus}


def disk_quota(lab_dir, cap_bytes):
    """Lab-dir size vs a cap; unreadable/missing dir is UNKNOWN, never PASS.

    `os.walk` silently skips unreadable directories, so blindness is detected
    explicitly: non-dir input and any walk/stat error yield UNKNOWN.
    """
    if not os.path.isdir(lab_dir):
        return {'status': 'UNKNOWN', 'reason': 'not a directory',
                'path': str(lab_dir)}
    errors = []

    def onerr(exc):
        errors.append(exc)

    try:
        total = 0
        for root, _, files in os.walk(lab_dir, onerror=onerr):
            for filename in files:
                try:
                    total += os.path.getsize(os.path.join(root, filename))
                except OSError as exc:
                    errors.append(exc)
    except OSError as exc:
        errors.append(exc)
    if errors:
        return {'status': 'UNKNOWN', 'reason': type(errors[0]).__name__,
                'path': str(lab_dir)}
    status = 'FAIL' if total > cap_bytes else 'PASS'
    return {'status': status, 'bytes_used': total, 'cap_bytes': cap_bytes,
            'path': str(lab_dir)}


def collect_all(path='.'):
    """Reference checks + plugins, one dict (UNKNOWN where blind)."""
    base = project.collect(path)
    base['checks']['memory'] = memory()
    base['checks']['dns_localhost'] = dns('localhost')
    base['checks']['dns_invalid'] = dns('no-such-host.invalid')
    base['checks']['load_detail'] = load()
    return base
