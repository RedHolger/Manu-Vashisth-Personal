"""Differential verification for SiliconCheck (P21-02): RTL vs Python model.

Seeded randomized read/write/reset traces drive `tb_diff.sv`; the logged
cycle-by-cycle RTL outputs are compared against the untouched reference
`project.FIFO`. Directed traces cover wraparound, simultaneous read/write
and reset-mid-transaction explicitly. Any mismatch preserves its seed, trace
and RTL result — a harness that cannot fail is not a harness.
"""
import random
import re
import shutil
import subprocess
from pathlib import Path

import project
import rtl

DEPTH = 4
FIELDS = ('cycle', 'wa', 'ra', 'data_out', 'full', 'empty')


def gen_trace(seed, cycles=200, reset_prob=0.05):
    """Seeded (wr, rd, data, rst) trace; resets sometimes carry wr/rd."""
    rng = random.Random(seed)
    trace = []
    for _ in range(cycles):
        rst = 1 if rng.random() < reset_prob else 0
        wr = rng.randrange(2)
        rd = rng.randrange(2)
        data = rng.randrange(256)
        trace.append((wr, rd, data, rst))
    return trace


def directed_traces():
    """Hand-built wraparound / simultaneous / reset-mid-transaction traces."""
    wrap = ([(1, 0, 10 + i, 0) for i in range(4)]      # fill 10..13
            + [(0, 1, 0, 0), (0, 1, 0, 0)]              # drain 2 (10,11)
            + [(1, 0, 20 + i, 0) for i in range(2)]     # wrap pointers (20,21)
            + [(0, 1, 0, 0)] * 4)                       # drain 12,13,20,21
    simul = ([(1, 0, 30 + i, 0) for i in range(2)]      # half-full
             + [(1, 1, 40 + i, 0) for i in range(6)]    # simultaneous x6
             + [(0, 1, 0, 0)] * 4)                      # drain rest
    reset_mid = ([(1, 0, 50 + i, 0) for i in range(3)]  # 3 entries live
                 + [(1, 1, 99, 1)]                      # reset WITH wr+rd
                 + [(1, 0, 60 + i, 0) for i in range(2)]
                 + [(0, 1, 0, 0)] * 2)                  # drain 60,61
    return {'wraparound': wrap, 'simultaneous': simul,
            'reset_mid_transaction': reset_mid}


def write_trace(path, trace):
    Path(path).write_text(''.join('%d %d %d %d\n' % t for t in trace),
                          encoding='utf-8')


def run_rtl(trace_path, workdir, dut='fifo.sv', tag='run'):
    """Compile `dut` + tb_diff, simulate on `trace_path`; parse result.log."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    for name in ('tb_diff.sv', dut):
        shutil.copy(name, workdir / Path(name).name)
    shutil.copy(trace_path, workdir / 'trace.txt')
    comp = rtl.compile_rtl([Path(dut).name, 'tb_diff.sv'],
                           'diff_%s.vvp' % tag, workdir=str(workdir))
    if comp['exit'] != 0:
        return {'compile': comp, 'simulate': None, 'results': None}
    sim = rtl.simulate('diff_%s.vvp' % tag, workdir=str(workdir))
    results = []
    log_path = workdir / 'result.log'
    if log_path.exists():
        for line in log_path.read_text(encoding='utf-8').splitlines():
            parts = line.split()
            if len(parts) == 6:
                results.append({k: int(v)
                                for k, v in zip(FIELDS, parts)})
    return {'compile': comp, 'simulate': sim, 'results': results,
            'vcd': str(workdir / 'trace.vcd')}


def compare(trace, results, depth=DEPTH):
    """Cycle-by-cycle RTL-vs-model diff; returns the mismatch list."""
    model = project.FIFO(depth=depth)
    mismatches = []
    for i, ((wr, rd, data, rst), rtl_row) in enumerate(zip(trace, results)):
        step = model.step(write=bool(wr), read=bool(rd), value=data,
                          reset=bool(rst))
        expected = {'wa': int(step['write_accepted']),
                    'ra': int(step['read_accepted']),
                    'full': int(step['count'] == depth),
                    'empty': int(step['count'] == 0)}
        actual = {'wa': rtl_row['wa'], 'ra': rtl_row['ra'],
                  'full': rtl_row['full'], 'empty': rtl_row['empty']}
        for field in ('wa', 'ra', 'full', 'empty'):
            if expected[field] != actual[field]:
                mismatches.append({'cycle': i, 'field': field,
                                   'expected': expected[field],
                                   'actual': actual[field],
                                   'stimulus': {'wr': wr, 'rd': rd,
                                                'data': data, 'rst': rst}})
        if step['read_accepted'] and not rst:
            if rtl_row['data_out'] != step['read_value']:
                mismatches.append({'cycle': i, 'field': 'data_out',
                                   'expected': step['read_value'],
                                   'actual': rtl_row['data_out'],
                                   'stimulus': {'wr': wr, 'rd': rd,
                                                'data': data, 'rst': rst}})
    if len(results) != len(trace):
        mismatches.append({'cycle': -1, 'field': 'cycle_count',
                           'expected': len(trace), 'actual': len(results),
                           'stimulus': {}})
    return mismatches


def run_seed(seed, cycles=200, dut='fifo.sv', workdir='.', tag=None):
    """Full pipeline for one seed; preserves the failing seed on mismatch."""
    tag = tag or ('seed-%d' % seed)
    work = Path(workdir) / tag
    trace = gen_trace(seed, cycles)
    # Stage the trace via a temp file; run_rtl copies it into the run dir.
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.txt',
                                     delete=False) as handle:
        handle.write(''.join('%d %d %d %d\n' % t for t in trace))
        trace_path = handle.name
    try:
        out = run_rtl(trace_path, work, dut=dut, tag=tag)
    finally:
        Path(trace_path).unlink(missing_ok=True)
    mismatches = compare(trace, out['results'] or []) \
        if out['results'] is not None else []
    return {'seed': seed, 'cycles': cycles, 'dut': dut,
            'mismatches': mismatches, 'n_mismatches': len(mismatches),
            'compile_exit': out['compile']['exit'],
            'simulate_exit': out['simulate']['exit']
            if out['simulate'] else None,
            'trace': trace, 'results': out['results']}


def run_directed(name, trace, dut='fifo.sv', workdir='.'):
    """One directed trace through the same pipeline."""
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.txt',
                                     delete=False) as handle:
        handle.write(''.join('%d %d %d %d\n' % t for t in trace))
        trace_path = handle.name
    try:
        out = run_rtl(trace_path, Path(workdir) / ('directed-' + name),
                      dut=dut, tag='directed-' + name)
    finally:
        Path(trace_path).unlink(missing_ok=True)
    mismatches = compare(trace, out['results'] or []) \
        if out['results'] is not None else []
    return {'name': name, 'cycles': len(trace), 'dut': dut,
            'mismatches': mismatches, 'n_mismatches': len(mismatches)}
