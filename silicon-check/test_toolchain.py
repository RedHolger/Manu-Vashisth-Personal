"""P21-01: the RTL toolchain runs the kit testbench cleanly + records a wave."""
import hashlib
import json
import unittest
from pathlib import Path

import rtl

KIT_HASHES = json.loads(Path('kit-sha256.txt').read_text(
    encoding='utf-8'))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ToolchainTests(unittest.TestCase):
    def test_iverilog_version_pinned(self):
        version = rtl.iverilog_version()
        self.assertIn('Icarus Verilog', version)
        self.assertRegex(version, r'version \d+')

    def test_kit_rtl_unmodified(self):
        for name in ('fifo.sv', 'tb.sv'):
            self.assertEqual(_sha(name), KIT_HASHES[name],
                             '%s differs from the recorded kit hash' % name)

    def test_compile_clean(self):
        result = rtl.compile_rtl(['fifo.sv', 'tb.sv'], 'tb_check.vvp')
        self.assertEqual(result['exit'], 0, result['log'])
        self.assertEqual(result['warnings'], [])

    def test_directed_sim_pass(self):
        rtl.compile_rtl(['fifo.sv', 'tb.sv'], 'tb_check.vvp')
        result = rtl.simulate('tb_check.vvp')
        self.assertEqual(result['exit'], 0, result['log'])
        self.assertIn('PASS directed RTL FIFO test', result['log'])

    def test_waveform_recorded(self):
        rtl.compile_rtl(['fifo.sv', 'tb_wave.sv'], 'tb_wave_check.vvp')
        result = rtl.simulate('tb_wave_check.vvp')
        self.assertEqual(result['exit'], 0, result['log'])
        vcd = Path('directed.vcd')
        self.assertTrue(vcd.exists())
        self.assertGreater(vcd.stat().st_size, 0)
        text = vcd.read_text(encoding='utf-8', errors='replace')
        for signal in ('full', 'empty', 'data_out', 'wr_accepted'):
            self.assertIn(signal, text)


if __name__ == '__main__':
    unittest.main()
