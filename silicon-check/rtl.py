"""RTL toolchain helper for SiliconCheck (P21): iverilog compile + simulate.

All simulation evidence flows through here so versions, commands, exit codes
and logs are captured uniformly. No step is allowed to fail silently: every
run returns its exit code and full text output.
"""
import subprocess

IVERILOG_FLAGS = ['-g2012']


def iverilog_version():
    proc = subprocess.run(['iverilog', '-V'], capture_output=True, text=True,
                          timeout=30)
    first = (proc.stdout + proc.stderr).splitlines()
    return first[0].strip() if first else 'unknown'


def compile_rtl(sources, vvp_path, workdir='.'):
    """Compile SystemVerilog `sources` to `vvp_path`. Returns dict."""
    cmd = ['iverilog'] + IVERILOG_FLAGS + ['-o', str(vvp_path)] + \
        [str(s) for s in sources]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          cwd=workdir)
    log = (proc.stdout or '') + (proc.stderr or '')
    return {'command': ' '.join(cmd), 'exit': proc.returncode, 'log': log,
            'warnings': [ln for ln in log.splitlines() if 'warning' in
                         ln.lower()]}


def simulate(vvp_path, workdir='.', timeout_s=120):
    """Run a compiled `vvp` simulation. Returns dict."""
    cmd = ['vvp', str(vvp_path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout_s, cwd=workdir)
    except subprocess.TimeoutExpired as exc:
        return {'command': ' '.join(cmd), 'exit': 124,
                'log': 'TIMEOUT after %ds: %s' % (timeout_s, exc)}
    log = (proc.stdout or '') + (proc.stderr or '')
    return {'command': ' '.join(cmd), 'exit': proc.returncode, 'log': log}


def toolchain():
    return {'simulator': 'Icarus Verilog', 'version': iverilog_version(),
            'flags': ' '.join(IVERILOG_FLAGS)}
