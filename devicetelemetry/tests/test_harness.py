"""Harness tests: CRC, gaps, reorder, range, transitions. Uses sim outputs as fixtures."""
import subprocess
import sys
import unittest

sys.path.insert(0, "src")
from harness import Monitor, crc16, parse_frame, run

SIM = "build/sim"


def stream(scenario, seed="7"):
    p = subprocess.run([SIM, scenario, seed], capture_output=True, text=True, check=True)
    return p.stdout.splitlines()


class TestFrames(unittest.TestCase):
    def test_crc16_known_vector(self):
        self.assertEqual(crc16(b"123456789"), 0x29B1)  # CRC-16/CCITT-FALSE check

    def test_clean_stream_streams(self):
        rep = run(stream("clean"))
        self.assertEqual(rep["final_state"], "STREAMING")
        self.assertEqual(rep["event_kinds"], [])

    def test_corrupt_frames_fault(self):
        rep = run(stream("corrupt"))
        self.assertEqual(rep["final_state"], "FAULT")
        kinds = rep["event_kinds"]
        self.assertIn("CORRUPT_FRAME", kinds)
        # two corrupt frames injected
        self.assertEqual(sum(1 for e in rep["events"] if e["type"] == "CORRUPT_FRAME"), 2)

    def test_dropped_frames_gap(self):
        rep = run(stream("drop"))
        self.assertIn("SEQ_GAP", rep["event_kinds"])
        self.assertNotIn("CORRUPT_FRAME", rep["event_kinds"])
        self.assertEqual(rep["final_state"], "STREAMING")  # gaps don't latch FAULT

    def test_reordered_frames_regression(self):
        rep = run(stream("reorder"))
        self.assertIn("SEQ_REGRESSION", rep["event_kinds"])

    def test_out_of_range_faults(self):
        rep = run(stream("range"))
        self.assertEqual(rep["final_state"], "FAULT")
        self.assertIn("OUT_OF_RANGE", rep["event_kinds"])

    def test_reset_ack_clears_fault(self):
        mon = Monitor()
        mon.feed({"ok": False, "error": "bad-crc", "lineno": 1})
        self.assertEqual(mon.state, "FAULT")
        mon.feed({"ok": True, "seq": 3, "type": 0x03, "value": 0, "lineno": 2})
        self.assertEqual(mon.state, "IDLE")
        self.assertIn("RESET_OK", [e["type"] for e in mon.events])

    def test_bad_length_and_sync(self):
        self.assertEqual(parse_frame("A55A", 1)["error"], "bad-length")
        bad = bytearray.fromhex("DEADBEEF0102030405060708")
        r = parse_frame(bad.hex(), 2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "bad-sync")


if __name__ == "__main__":
    unittest.main(verbosity=2)
