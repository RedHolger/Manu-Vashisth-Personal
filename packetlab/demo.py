"""Demo: run diagnostics over all fixtures, save timestamped evidence records."""
import json
import sys

sys.path.insert(0, "src")
from diagnostics import correlate, load_loss_series, parse_bgp_summary, parse_ip_route

EXPECTED = {"10.1.0.0/24": "192.0.2.2", "10.2.0.0/24": "192.0.2.2"}

scenarios = {
    "healthy": ("bgp_healthy.txt", "routes_ok.txt", "loss_clean.csv"),
    "peer-down": ("bgp_peerdown.txt", "routes_ok.txt", "loss_spike.csv"),
    "wrong-route": ("bgp_healthy.txt", "routes_wrong.txt", "loss_clean.csv"),
}

report = {}
for name, (b, r, l) in scenarios.items():
    with open(f"fixtures/{b}") as fh:
        peers = parse_bgp_summary(fh.read())
    with open(f"fixtures/{r}") as fh:
        routes = parse_ip_route(fh.read())
    loss = load_loss_series(f"fixtures/{l}")
    report[name] = correlate(peers, routes, EXPECTED, loss)

with open("results/demo_evidence.json", "w") as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
