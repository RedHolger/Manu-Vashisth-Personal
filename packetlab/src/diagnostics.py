"""Read-only BGP/route diagnostics. Parses FRR-style command text; stdlib only."""
import csv
import re
from dataclasses import dataclass


@dataclass
class PeerState:
    neighbor: str
    asn: str
    state: str  # e.g. Established, Active, Idle


def parse_bgp_summary(text: str) -> list[PeerState]:
    peers: list[PeerState] = []
    for line in text.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+)\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)\s*$", line.strip())
        if m:
            raw = m.group(3).strip()
            # FRR shows a received-prefix COUNT for established peers and a
            # state name (Active/Idle/...) otherwise; normalize digits.
            state = "Established" if raw.isdigit() else raw
            peers.append(PeerState(neighbor=m.group(1), asn=m.group(2), state=state))
    return peers


def parse_ip_route(text: str) -> dict[str, tuple[str, str]]:
    """prefix -> (nexthop, protocol). Handles 'B>* 10.0.0.0/24 [20/0] via 192.0.2.1' lines."""
    routes: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Z])[>]?[*]?\s+(\S+)\s+\[[^\]]*\]\s+via\s+(\S+)", line.strip())
        if m:
            routes[m.group(2)] = (m.group(3).rstrip(","), m.group(1))
    return routes


def load_loss_series(path: str) -> list[tuple[str, float]]:
    with open(path, newline="") as fh:
        return [(row["ts"], float(row["loss_pct"])) for row in csv.DictReader(fh)]


def correlate(peers: list[PeerState], routes: dict[str, tuple[str, str]],
              expected: dict[str, str], loss: list[tuple[str, float]],
              loss_threshold: float = 5.0) -> list[dict]:
    """Build timestamped failure-evidence records. expected: prefix -> nexthop."""
    events: list[dict] = []
    down = [p.neighbor for p in peers if p.state != "Established"]
    for nb in down:
        events.append({"type": "PEER_DOWN", "detail": nb})
    for prefix, want_nh in expected.items():
        got = routes.get(prefix)
        if got is None:
            events.append({"type": "PREFIX_MISSING", "detail": prefix})
        elif got[0] != want_nh:
            events.append({"type": "WRONG_ROUTE",
                           "detail": f"{prefix} via {got[0]} (expected {want_nh})"})
    bad = [(ts, v) for ts, v in loss if v >= loss_threshold]
    if bad and not down:
        events.append({"type": "LOSS", "detail": f"{len(bad)} samples >= {loss_threshold}% "
                                                 f"with peers up (first {bad[0][0]})"})
    if not events and loss:
        events.append({"type": "RECOVERED", "detail": f"peers up, routes correct, "
                       f"max loss {max(v for _, v in loss):.1f}% over {len(loss)} samples"})
    return events
