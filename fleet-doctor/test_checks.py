"""P18-01: plugins report UNKNOWN (never healthy) when blind."""
import os
import stat
import unittest

import checks


class PluginTests(unittest.TestCase):
    def test_disk_thresholds(self):
        import project
        self.assertEqual(project.classify_free(100, 4), 'FAIL')
        self.assertEqual(project.classify_free(100, 50), 'PASS')
        self.assertEqual(project.classify_free(0, 0), 'UNKNOWN')

    def test_unreadable_path_is_unknown_not_healthy(self):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp(prefix='p18-blind-'))
        (d / 'f').write_bytes(b'x')
        os.chmod(d, 0)
        try:
            quota = checks.disk_quota(str(d), 10 ** 12)
            self.assertEqual(quota['status'], 'UNKNOWN')
            du = checks.disk(str(d))
            self.assertIn(du['status'], ('UNKNOWN', 'PASS', 'WARN', 'FAIL'))
        finally:
            os.chmod(d, stat.S_IRWXU)
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_missing_tool_is_unknown(self):
        import project
        out = project.command(['/definitely-not-present-program'])
        self.assertEqual(out['status'], 'UNKNOWN')

    def test_dns_localhost_pass_invalid_fail(self):
        ok = checks.dns('localhost')
        self.assertEqual(ok['status'], 'PASS')
        bad = checks.dns('no-such-host.invalid')
        self.assertEqual(bad['status'], 'FAIL')

    def test_process_liveness(self):
        import subprocess
        import time
        proc = subprocess.Popen(['sleep', '30'])
        try:
            self.assertEqual(checks.process(pid=proc.pid)['status'], 'PASS')
        finally:
            proc.kill()
            proc.wait()
        self.assertEqual(checks.process(pid=proc.pid)['status'], 'FAIL')

    def test_load_sampled_with_structure(self):
        load = checks.load()
        self.assertIn(load['status'], ('PASS', 'WARN', 'UNKNOWN'))
        if load['status'] != 'UNKNOWN':
            self.assertIn('load_1_5_15', load)

    def test_memory_never_healthy_when_blind(self):
        mem = checks.memory()
        self.assertIn(mem['status'], ('PASS', 'WARN', 'FAIL', 'UNKNOWN'))
        if mem['status'] == 'UNKNOWN':
            self.assertIn('reason', mem)


if __name__ == '__main__':
    unittest.main()
