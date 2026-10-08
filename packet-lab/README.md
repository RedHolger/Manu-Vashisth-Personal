# PacketLab — offline network-troubleshooting lab

Practice break/fix without touching a real network: a versioned topology spec
whose admin guard refuses non-lab targets (every operation is a dry run), four
ground-truthed fault fixtures (DNS, blackhole, MTU clamp, stalled service)
with byte-identical reset, an open-format capture parser (secrets redacted,
malformed and binary input rejected with reasons, per-file hashes), and a
runbook that retains wrong hypotheses and splits measured collection time
from human reasoning time (no analyst, none claimed). Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 18 tests
```

All fixture IPs are documentation ranges. Live namespaces/VMs and analyst
timing need grants and people not present here.

## Limits

Fixtures, not live faults; a text-format parser, not a pcap tool; no human
reasoned here. Reset is byte-reproducibility, not a live reset command.
