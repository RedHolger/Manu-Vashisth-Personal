# CloudSupport — LIMITATIONS

- All cases run on loopback with synthetic services; not real AWS APIs,
  production incidents, or customer cases. No certification implied.
- TLS uses a throwaway 2-day self-signed cert minted at runtime; it validates
  the diagnostic workflow, not PKI operations.
- DNS case assumes `.invalid` stays non-resolvable (RFC 2606) and no wildcard
  resolver interferes; the case reports failure honestly if it resolves.
- Timing margins (2.5 s vs 0.5 s) are generous but machine-dependent; not a
  performance benchmark.
- Local-machine results (macOS, Python 3.14.7, OpenSSL 3.5.7), not
  cross-platform guarantees.
- Supports role 34 only as documented troubleshooting work.
