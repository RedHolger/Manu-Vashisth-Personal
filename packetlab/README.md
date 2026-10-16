# PacketLab

A routing troubleshooting lab with an offline diagnostic path and a live two-peer FRR eBGP experiment. It records route tables and timestamps so a fault can be followed from injection through withdrawal and recovery.

The live experiment covers three cases: a stopped peer, an incorrect advertised prefix and 100% packet loss. The saved run used FRR 10.2.1 and recovered from all three cases.

## Offline checks

With Python 3, run from this directory:

```bash
python3 -m unittest discover -s tests -v
python3 demo.py
```

## Live BGP experiment

```bash
python3 live_frr.py
```

This requires a running Docker engine and access to the FRR image. It creates two temporary containers and a bridge network, grants `NET_ADMIN` inside the containers for packet-loss injection, and cleans up its own resources on exit. It does not expose public ports or change host routes.

`results/live_frr.json` contains the saved route and event evidence. The experiment checks the BGP control plane, not kernel forwarding or hardware performance. [EVIDENCE.md](EVIDENCE.md) and [LIMITATIONS.md](LIMITATIONS.md) describe that boundary.
