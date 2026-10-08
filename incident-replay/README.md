# IncidentReplay — reproducible incident investigation

A workbench for practicing incident response on fixture incidents: two log
formats ingested with provenance (timezones, dedup, clock skew and missing
records surface as uncertainty), deterministic detectors scored against
ground truth (precision/recall with counts, plus benign look-alikes for false
positives), evidence-linked executive/technical reports, and a hardened
replay showing the same attacks blocked at the service. Pure Python, stdlib
only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 126 tests
```

Recorded: indicator rule catches half the attacks (with legitimate fires);
sequence detector catches 3/4 with none; one insider scenario missed by both
(reported as the costliest miss). Hardened replay (detectors untouched): all
four exfiltrations go to 0 bytes, legitimate bulk byte-identical, zero new
false positives.

## Limits

Fully synthetic logs (invented hosts, RFC-reserved IPs); text-format parsing,
no PCAP; no real incidents, no analyst time measured. Remediation is a
modeled control, not a production deployment.
