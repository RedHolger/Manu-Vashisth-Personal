"""Evidence-kind separation for SiliconCheck (P21-04).

Probes synthesis/FPGA prerequisites and records the three evidence kinds
(simulation, synthesis, board) as SEPARATE statuses. Simulation is VERIFIED;
synthesis and board are BLOCKED here. Nothing is simulated, substituted or
conflated: a missing toolchain/equipment yields BLOCKED, never a fake PASS.
"""
import json
import shutil
from pathlib import Path

SIM_RESULTS = ['results/p21-01-toolchain/toolchain-report.json',
               'results/p21-02-differential/differential.json',
               'results/p21-03-quality/quality.json']


def probe_synthesis():
    found = shutil.which('yosys') is not None
    return {'available': found, 'tool': 'yosys',
            'status': 'READY' if found else 'BLOCKED',
            'note': 'yosys present' if found else 'no yosys binary; no '
                    'netlist, area or timing evidence exists'}


def probe_fpga():
    tools = {name: shutil.which(name) is not None
             for name in ('quartus', 'vivado', 'openFPGALoader', 'nextpnr',
                          'icestorm')}
    any_tool = any(tools.values())
    return {'tools': tools, 'board_inventoried': False,
            'status': 'READY' if (any_tool) else 'BLOCKED',
            'note': 'no FPGA toolchain and no board inventoried; no '
                    'bitstream or on-device evidence exists'}


def _sim_verified():
    for rel in SIM_RESULTS:
        path = Path(__file__).parent / rel
        if not path.exists():
            return False, 'missing %s' % rel
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            return False, 'unparseable %s' % rel
        if report.get('all_met') is not True:
            return False, '%s not all_met' % rel
    return True, 'p21-01/02/03 reports exist and all_met'


def evidence_kinds():
    sim_ok, sim_note = _sim_verified()
    synth = probe_synthesis()
    fpga = probe_fpga()
    return {
        'simulation': {'status': 'VERIFIED' if sim_ok else 'NOT_VERIFIED',
                       'note': sim_note,
                       'paths': list(SIM_RESULTS)},
        'synthesis': {'status': synth['status'], 'note': synth['note']},
        'board': {'status': fpga['status'], 'note': fpga['note']},
    }


NEGATIONS = ('not ', 'never ', 'no ', 'is not ', 'are not ', 'without ',
             'refuse', 'blocked', "isn't", "aren't", 'neither ', 'nor ')


def no_conflation(root='results'):
    """Lines claiming a synthesis/board PASS, excluding negated disclaimers.

    A line like 'simulation success is not silicon sign-off' is a disclaimer,
    not a claim, so same-line negations exempt it. An affirmative claim line
    ('synthesis pass', 'board pass achieved') carries no negation and is
    flagged. Case-insensitive.
    """
    bad = []
    for path in Path(root).rglob('*.json'):
        if path.name.startswith('._'):
            continue
        try:
            lines = path.read_text(encoding='utf-8').lower().splitlines()
        except (ValueError, OSError):
            continue
        flagged = False
        for line in lines:
            for claim in ('synthesis pass', 'synth pass', 'fpga pass',
                          'board pass', 'silicon sign-off'):
                if claim in line and not any(n in line for n in NEGATIONS):
                    flagged = True
        # Path only (never the raw claim string) so an audit report
        # recording its own hits cannot re-trigger.
        if flagged:
            bad.append(str(path))
    return sorted(set(bad))
