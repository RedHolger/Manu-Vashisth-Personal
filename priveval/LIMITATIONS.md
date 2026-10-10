# PrivacyEval — LIMITATIONS

- Synthetic two-tenant toy corpus; not a production access-control audit.
- Extractive quoter, no LLM: measures retrieval/authorization controls, NOT
  prompt-injection robustness of a generative model. No red-team claims.
- Canaries are obvious `*-canary-*` fixtures; a real secret-hunt would differ.
- Frozen sets are tiny (12/8); Wilson intervals are wide by construction.
- Authorization ≠ differential privacy, stated in CV wording too.
- Local-machine, single-run determinism (no randomness involved).
- Supports role 33 only as controls-evaluation work.
