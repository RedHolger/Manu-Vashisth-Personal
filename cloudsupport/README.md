# CloudSupport Casebook

Five small troubleshooting exercises that reproduce a failure, diagnose it, apply a fix and check recovery. The cases cover DNS lookup failure, refused TCP connections, HTTP timeouts, a TLS hostname mismatch and an expired signed upload.

Each case runs locally and records timestamped evidence. This makes it possible to inspect the failing and recovered states without an AWS account or a running customer service.

## Run the cases

Use Python 3 and the `openssl` command for the TLS exercise. Run from this directory:

```bash
python3 -m unittest discover -s tests -v
python3 runbook.py
```

The runbook writes `results/casebook.json` and returns a nonzero exit code if a case fails. Local loopback sockets are required; the exercises do not call a cloud API.

The implementations are in `src/cases.py`. See [SPEC.md](SPEC.md) for the expected failure and recovery conditions, and [EVIDENCE.md](EVIDENCE.md) for saved runs.
