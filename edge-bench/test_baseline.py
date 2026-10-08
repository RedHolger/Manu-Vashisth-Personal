"""P20-02/04: per-frame baseline, drops, overruns, restart; power BLOCKED."""
import unittest

import baseline
import instruments
import workload
from instruments import BlockedError


class BaselineTests(unittest.TestCase):
    def test_per_frame_log_and_variability(self):
        out = baseline.run('baseline', n=12, size=32, seed=7)
        self.assertEqual(len(out['milliseconds']), 12)
        self.assertEqual(out['dropped'], 0)
        for key in ('min_ms', 'p50_ms', 'p95_ms', 'max_ms', 'std_ms'):
            self.assertIn(key, out['stats'])
        self.assertLessEqual(out['stats']['min_ms'], out['stats']['p95_ms'])
        self.assertLessEqual(out['stats']['p95_ms'], out['stats']['max_ms'])

    def test_dropped_frames_counted_not_crashed(self):
        frames = workload.make_frames(4, 16, 7) + [[[1]], 'bad', [[1] * 2] * 2]
        out = baseline.run_with_drops('baseline', frames)
        self.assertEqual(out['dropped'], 3)
        self.assertEqual(len(out['milliseconds']), 4)

    def test_watchdog_flags_overruns(self):
        out = baseline.run('baseline', n=6, size=32, seed=7,
                           watchdog_ms=0.0)
        self.assertEqual(len(out['overruns']), 6)
        out2 = baseline.run('baseline', n=6, size=32, seed=7,
                            watchdog_ms=1e9)
        self.assertEqual(out2['overruns'], [])

    def test_restart_deterministic(self):
        a = baseline.run('baseline', n=10, size=32, seed=7)
        b = baseline.run('baseline', n=10, size=32, seed=7)
        self.assertEqual(a['output_checksum'], b['output_checksum'])

    def test_environment_honest(self):
        env = baseline.environment()
        self.assertEqual(env['device'], 'host-cpu')
        self.assertFalse(env['board_tested'])
        self.assertIsNone(env['power_watts'])
        self.assertIsNone(env['temperature_c'])


class InstrumentTests(unittest.TestCase):
    def test_power_and_thermal_blocked(self):
        man = instruments.manifest()
        self.assertIsNone(man['power_watts'])
        self.assertIsNone(man['temperature_c'])
        self.assertEqual(man['power']['status'], 'BLOCKED')
        self.assertEqual(man['thermal']['status'], 'BLOCKED')

    def test_measured_fields_raise(self):
        with self.assertRaises(BlockedError):
            instruments.measured_watts()
        with self.assertRaises(BlockedError):
            instruments.measured_temperature()


if __name__ == '__main__':
    unittest.main()
