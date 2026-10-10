# CloudSupport — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, system Python 3.14.7 stdlib only, OpenSSL 3.5.7 CLI,
loopback only. No third-party packages.

## Commands (exit 0)

- `python -m unittest discover -s tests -v` → 6/6 OK (~7 s, dominated by the
  2.5 s `/slow` handler sleep).
- `python runbook.py` → `results/casebook.json`: 5/5 pass
  (dns_unresolvable, tcp_refused, http_timeout, tls_hostname, upload_expiry),
  6–7 timestamped steps each.

## Measured behavior

- DNS: `.invalid` → gaierror EAI_NONAME; `localhost` → 127.0.0.1 (+ ::1).
- TCP: closed port → ECONNREFUSED errno 61; listener fix → banner `OK`.
- HTTP: `/slow` 2.5 s vs 0.5 s timeout → timeout error; 8 s retry → 200,
  body `slow-ok` sha256 verified; `/fast` control instant.
- TLS: self-signed CN=localhost/SAN=localhost; `wrongname.example` →
  CertificateError; `localhost` → verified 200 `tls-ok`.
- Upload: expired URL → 403 expired; fresh (+300 s) → 200, stored sha256
  matches; tampered sig → 403 bad-signature (stays rejected).

## Claim basis for CV 34 (role 34 only)

- "Built a local support casebook reproducing DNS, TCP-refused, HTTP-timeout,
  TLS-hostname and signed-upload-expiry failures with diagnostics, root cause,
  fix and verified recovery for each (5/5 automated, stdlib only)."
- "No cloud account, customer data, or certification claims."
