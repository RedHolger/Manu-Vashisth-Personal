# Current verification — 10 October 2026

`python live_frr.py` executed two isolated FRR 10.2.1 Docker peers, established eBGP, removed/restored a peer, substituted/restored an advertised prefix, and injected/removed 100% packet loss using tc netem. All three fault/recovery scenarios passed. Timestamped real route tables and initial BGP summary are in results/live_frr.json. Task-created containers and bridge were removed in finally cleanup. Existing fixture tests remain separate.

Scope is the BGP control plane; this does not test kernel forwarding, production networks, hardware or containerlab. Docker and container NET_ADMIN are needed only for the isolated live test. No public ports or host route changes.
