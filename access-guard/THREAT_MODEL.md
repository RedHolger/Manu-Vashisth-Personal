# AccessGuard threat model

Card: **P11-04**. Scope of this document: the authorization test harness in
this folder (`policy_oracle.py`, `lab_app.py`, `runner.py`, `regression.py`)
and the loopback lab service it tests. It is not a threat model for any
production system, and it is not a threat model for P04 FlowLedger or P05
EvidenceRAG.

**Finite cases do not prove universal security.** Everything below describes
what this harness can and cannot observe, so a reviewer can check each claim
against the evidence instead of trusting the author.
Finite cases do not prove universal security: the 22-case matrix covers
4 planted bug classes (not the space of authorization flaws).

## Scope

In scope:

- Object-level authorization on a single-resource HTTP API (`read` via GET,
  `write` via POST, `delete` via DELETE) served by `lab_app.py` on
  `127.0.0.1` at an ephemeral port.
- Tenant isolation between two tenants (A, B) across five principals.
- Session lifecycle: expiry (epoch-bearing tokens) and server-side
  revocation, evaluated on every request.
- Privilege correctness: the effective role comes from the server-side
  registry on every request; the token's claimed role is never trusted, so a
  demotion takes effect immediately and a forged admin claim is denied.
- Input validation: a closed action vocabulary (unknown methods → 405) and
  malformed-token / unknown-resource denials (401/404). All fail closed.
- Evidence hygiene: bearer values never enter a report; records carry the
  principal id and the expected reason, never the token.

Out of scope: everything under *Unsupported attacker capabilities*, and every
property of a real deployment (TLS, rate limiting, persistent session stores,
multi-instance consistency).

## Trusted boundaries

| # | Boundary | Trusted side | Untrusted side | Why the line is there |
|---|---|---|---|---|
| B1 | HTTP request → service decision point | the service's revocation set, role registry and document table | everything in the request: bearer token, tenant/doc ids, method | Authorization input is attacker-controlled by definition; service state is not. |
| B2 | Oracle → target independence | `policy_oracle.py` and its rule evaluation | `lab_app.py` and its responses | The oracle is the specification. An AST-level import scan (`test_http_adapter.py`) proves neither module imports the other; if the oracle consulted the target it would report agreement, not correctness. |
| B3 | Lab process → network | the loopback interface | every non-loopback interface | Servers bind `127.0.0.1` on ephemeral ports; the runner addresses only the returned loopback URL. |
| B4 | Evidence files → reviewers | sanitized records | bearer token values | Reports are scanned for bearer values before they are accepted (`no_credentials_in_reports`); denied responses carry no document payload. |

The load-bearing boundary is **B2**: expected and observed answers travel
along different code paths. `regression.py` additionally hash-guards the
oracle so it cannot be edited to make a target pass.

## Supported attacker capabilities

What the 22-case extended matrix actually exercises:

1. **Authenticated same-tenant principal writing another principal's object**
   (broken object-level authorization). 2 cases; both detected on the seeded
   target, both denied on the repaired target.
2. **Cross-tenant access, including by an administrator and via owner-id
   confusion** (a B-doc owned by an A-user). 3 cases; all detected, all denied
   after repair.
3. **Bearer replay after expiry and after revocation**, including replay by a
   would-be-authorized admin (`expired-admin-bypass`, `revoked-admin-bypass`).
   Both detected, both denied after repair.
4. **Privilege manipulation**: a demoted admin's delete is denied
   (server-side registry, no stale reach) and a forged admin claim is denied
   (token role ignored). Denied on both variants — correct enforcement, not a
   planted bug.
5. **Action/identifier abuse**: unknown method (PUT → 405), malformed token
   (→ 401), unknown resource (→ 404). All fail closed on both variants.
6. **Unauthenticated access**: missing bearer (→ 401). Fail closed.
7. **Response hygiene**: every record is checked to carry no bearer value.

Measured coverage: the seeded target shows **7 mismatches** over the 22-case
matrix (3 cross-tenant + 2 ownership + 1 expired-admin + 1 revoked-admin);
the repaired target shows **0 mismatches** over the same 22 cases. 7/7 seeded
findings and 0 false positives are counts over these 22 cases and these 4
planted bug classes — not rates over a population of implementations.

## Unsupported attacker capabilities

Explicitly **not** covered; every claim in this folder ends at this list:

1. **Token guessing, brute force or cryptanalysis.** Fixture tokens are
   deterministic strings, predictable by design. Nothing here tests token
   entropy, and token theft is assumed, not modeled.
2. **Network-position attacks**: no MITM, no TLS, no proxy/WAF normalization
   differences, no request smuggling. Plain HTTP/1.1 on loopback only.
3. **Concurrency and races**: no TOCTOU, no parallel requests, no
   session-fixation races. One sequential client.
4. **Injection into a real datastore**: the document table is an in-memory
   dict; no SQL, no ORM, no operator injection.
5. **Rate limiting and lockout**: the lab never throttles; burst tolerance is
   untested.
6. **Multi-instance session consistency**: one process, one revocation set;
   replication lag and split-brain revocation are untested.
7. **Privilege changes mid-request and admin-channel attacks**: there is no
   admin channel in this lab; role changes are applied between runs via the
   registry fixture.
8. **Human and process factors**: phishing, endpoint compromise, malicious
   operator, supply-chain backdoors. Out of scope for a code harness.

## Residual risks

Even within scope, a reviewer should know:

1. **403 vs 404 enumeration.** The fixed app returns 404 for unknown
   documents and 403 for forbidden ones, so an authenticated principal can
   probe document existence by status code. Accepted for a lab; a real service
   should consider uniform responses.
2. **Shared authorship of oracle and target.** One author wrote both the
   specification and the implementation under test. The import-scan and the
   hash-guard limit (but do not eliminate) the risk of a shared blind spot.
3. **Predictable fixture tokens.** Anyone who reads the source knows every
   token. Fine for a lab; fatal if copied into a real deployment.
4. **Sequential single-client execution.** Race-shaped flaws are invisible to
   this harness by construction.
5. **Fixed 5-principal, 4-document, 2-tenant fixture.** Coverage does not
   generalize to larger policy shapes; the tenant count in particular is
   minimal.

## What this evidence does not prove

- That any real system is secure, or that these 4 bug classes are absent
  anywhere but the repaired lab target on the 22 recorded cases.
- That the oracle itself is correct — it is a hand-written specification with
  the same single-author risk as the target. Its protection is reviewability
  (short, explicit rules with reasons), not authority.
- That passing this gate predicts passing any other assessment. It predicts
  exactly one thing: the repaired lab target denies the 22 recorded attacks.
