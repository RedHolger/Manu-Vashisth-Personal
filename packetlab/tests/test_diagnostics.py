"""Fixture tests: peer-down, wrong-route, loss/recovery, plan validation."""
import sys
import unittest

sys.path.insert(0, "src")
from diagnostics import correlate, load_loss_series, parse_bgp_summary, parse_ip_route
from faultplan import FaultPlan, validate

EXPECTED = {"10.1.0.0/24": "192.0.2.2", "10.2.0.0/24": "192.0.2.2"}


def load(name):
    with open(f"fixtures/{name}") as fh:
        return fh.read()


class TestDiagnostics(unittest.TestCase):
    def test_healthy_is_recovered(self):
        peers = parse_bgp_summary(load("bgp_healthy.txt"))
        self.assertEqual(len(peers), 2)
        self.assertTrue(all(p.state == "Established" for p in peers))
        routes = parse_ip_route(load("routes_ok.txt"))
        loss = load_loss_series("fixtures/loss_clean.csv")
        events = correlate(peers, routes, EXPECTED, loss)
        self.assertEqual([e["type"] for e in events], ["RECOVERED"])

    def test_peer_down_detected(self):
        peers = parse_bgp_summary(load("bgp_peerdown.txt"))
        states = {p.neighbor: p.state for p in peers}
        self.assertEqual(states["192.0.2.3"], "Active")
        routes = parse_ip_route(load("routes_ok.txt"))
        loss = load_loss_series("fixtures/loss_spike.csv")
        events = correlate(peers, routes, EXPECTED, loss)
        self.assertIn("PEER_DOWN", [e["type"] for e in events])

    def test_wrong_route_detected(self):
        peers = parse_bgp_summary(load("bgp_healthy.txt"))
        routes = parse_ip_route(load("routes_wrong.txt"))
        loss = load_loss_series("fixtures/loss_clean.csv")
        events = correlate(peers, routes, EXPECTED, loss)
        kinds = [e["type"] for e in events]
        self.assertIn("WRONG_ROUTE", kinds)
        self.assertNotIn("PEER_DOWN", kinds)

    def test_loss_with_peers_up_flagged(self):
        peers = parse_bgp_summary(load("bgp_healthy.txt"))
        routes = parse_ip_route(load("routes_ok.txt"))
        loss = load_loss_series("fixtures/loss_spike.csv")
        events = correlate(peers, routes, EXPECTED, loss)
        self.assertIn("LOSS", [e["type"] for e in events])

    def test_missing_prefix_flagged(self):
        peers = parse_bgp_summary(load("bgp_healthy.txt"))
        routes = parse_ip_route(load("routes_ok.txt"))
        loss = load_loss_series("fixtures/loss_clean.csv")
        events = correlate(peers, routes, {"10.9.0.0/24": "192.0.2.2"}, loss)
        self.assertIn("PREFIX_MISSING", [e["type"] for e in events])


class TestFaultPlan(unittest.TestCase):
    def good(self):
        return FaultPlan(target="r1:eth1", kind="peer-shutdown", max_duration_s=120,
                         affected_prefixes=["10.1.0.0/24"],
                         rollback=["no neighbor 192.0.2.3 shutdown", "verify Established"],
                         preconditions=["peers-established"])

    def test_valid_plan_passes(self):
        self.assertEqual(validate(self.good()), [])

    def test_rejects_unbounded_and_missing_rollback(self):
        bad = self.good()
        bad.max_duration_s = 3600
        bad.rollback = []
        errs = validate(bad)
        self.assertTrue(any("max_duration_s" in e for e in errs))
        self.assertTrue(any("rollback" in e for e in errs))

    def test_rejects_missing_preconditions_and_kind(self):
        bad = self.good()
        bad.kind = "nuke"
        bad.preconditions = []
        errs = validate(bad)
        self.assertTrue(any("unknown kind" in e for e in errs))
        self.assertTrue(any("preconditions" in e or "peers-established" in e for e in errs))

    def test_wrong_route_needs_prefixes(self):
        bad = self.good()
        bad.kind = "wrong-route"
        bad.affected_prefixes = []
        self.assertTrue(any("affected_prefixes" in e for e in validate(bad)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
