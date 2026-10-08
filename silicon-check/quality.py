"""Verification quality for SiliconCheck (P21-03): assertions + seeded defect.

`run_assertions()` replays a trace through `tb_assert.sv` against a DUT and
reports PASS/FAIL from the simulator (a $fatal is a nonzero exit, never a
silent pass). `coverage_report()` states covered properties and untested
parameter combinations honestly — simulation success is not silicon sign-off.
"""
import shutil
from pathlib import Path

import rtl

COVERED_PROPERTIES = [
    'reset clears occupancy, pointers, outputs and accept flags',
    'full/empty transitions at count==DEPTH / count==0',
    'overflow refused (write to full not accepted)',
    'underflow refused (read from empty not accepted)',
    'FIFO order preserved across fill/drain',
    'pointer wraparound (fill, partial drain, refill across the wrap)',
    'simultaneous read+write holds occupancy and preserves order',
    'reset mid-transaction (with live wr/rd) clears and ignores',
    'accept flags equal pre-edge occupancy (full+read rejects write)',
    'count stays within [0, DEPTH]',
    'seeded simultaneous-count defect is detected (P21-03)',
]

UNTESTED = [
    'DEPTH other than 4; WIDTH other than 8',
    'clock-domain crossing / multi-clock / async reset',
    'power-on (X-state) reset; X-propagation',
    'ready/valid backpressure handshake (this interface uses accept flags)',
    'gate-level timing, setup/hold, STA',
    'synthesis (no yosys) and FPGA/board (no equipment)',
    'formal equivalence vs the Python model',
]


def run_assertions(trace_path, dut='fifo.sv', workdir='.', tag='assert'):
    """Replay `trace_path` under tb_assert.sv; return PASS/FAIL + log."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    for name in ('tb_assert.sv', dut):
        shutil.copy(name, workdir / Path(name).name)
    shutil.copy(trace_path, workdir / 'trace.txt')
    comp = rtl.compile_rtl([Path(dut).name, 'tb_assert.sv'],
                           'assert_%s.vvp' % tag, workdir=str(workdir))
    if comp['exit'] != 0:
        return {'pass': False, 'compile': comp, 'simulate': None,
                'cycles': 0}
    sim = rtl.simulate('assert_%s.vvp' % tag, workdir=str(workdir))
    passed = sim['exit'] == 0 and 'PASS_ASSERTIONS' in sim['log']
    cycles = 0
    for line in sim['log'].splitlines():
        if 'PASS_ASSERTIONS cycles=' in line:
            try:
                cycles = int(line.split('cycles=')[1].split()[0])
            except ValueError:
                cycles = 0
    return {'pass': passed, 'compile': comp, 'simulate': sim,
            'cycles': cycles}


def coverage_report():
    return {'covered_properties': list(COVERED_PROPERTIES),
            'untested': list(UNTESTED),
            'signoff_disclaimer': 'simulation success is not silicon '
                                  'sign-off; no synthesis, timing or board '
                                  'evidence is claimed here'}
