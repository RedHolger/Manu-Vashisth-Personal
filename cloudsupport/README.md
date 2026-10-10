# CloudSupport Casebook — local support-case lab (role 34)

Five reproducible loopback cases with setup/cleanup and recovery proof.
Stdlib Python only (+ `openssl` CLI for the TLS case). No network, no cloud.

## Setup

```
python -m unittest discover -s tests -v   # 6 tests (venv: ../../../.venv-builds)
python runbook.py                          # all cases -> results/casebook.json
```

## Layout

- `SPEC.md` — cases, evidence format, scope limits.
- `src/cases.py` — the five cases, each returning timestamped evidence.
- `runbook.py` — runs all, writes `results/casebook.json`, exit 1 on failure.
- `tests/test_cases.py` — failure-reproduces + recovery-succeeds per case.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
