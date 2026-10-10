# CloudSupport Casebook — SPEC (Milestone 1)

Scope: reproducible LOCAL support cases for role 34 (AWS Cloud Support Associate).
Stdlib Python only; loopback interface only; no paid cloud, no external network
(all names/ports are localhost or RFC-2606 `.invalid`).

## Cases (each: symptom → diagnostics → root cause → fix → recovery proof)

1. **dns_unresolvable** — `socket.getaddrinfo('no-such-host.invalid')` raises
   `gaierror`. Diagnose: resolver error text + `.invalid` is non-resolvable by
   design (RFC 2606). Fix path: correct hostname `localhost`. Recovery proof:
   `localhost` → `127.0.0.1`.
2. **tcp_refused** — connect to a verified-closed loopback port → ECONNREFUSED
   (errno 61 macOS / 111 Linux; both accepted). Diagnose: errno + "nothing
   listening". Fix: start listener on that port, reconnect, banner exchange OK.
3. **http_timeout** — in-process `http.server`, `/slow` sleeps 2.5 s; client
   `timeout=0.5` → `TimeoutError`. Diagnose: elapsed ≥ timeout, server healthy
   (control `/fast` answers instantly). Fix: timeout 5 s + one backoff retry →
   200 with expected body sha256.
4. **tls_hostname** — openssl-minted self-signed cert (CN=localhost, SAN
   localhost) in temp dir; HTTPS server; client `server_hostname=
   'wrongname.example'` trusting the cert → `ssl.CertificateError`. Diagnose:
   requested name vs cert SAN/CN. Fix: `server_hostname='localhost'` → 200,
   verified chain. If `openssl` is missing this case is SKIPPED with reason.
5. **upload_expiry** — HMAC-signed upload URL (`?exp=<epoch>&sig=<hmac-sha256>`)
   served by local HTTP endpoint. Expired `exp` → 403 "expired". Diagnose:
   server-now vs exp (replay/expiry, not signature). Fix: mint fresh URL
   (exp=+300 s) → 200, bytes stored, sha256 matches. Tampered sig → 403
   (negative test, stays rejected).

## Evidence + customer note

`runbook.py` runs all cases with setup/cleanup (temp dirs, thread servers with
shutdown) and writes `results/casebook.json`: per case, timestamped steps
{symptom, diagnostics, root_cause, fix, recovery_proof, customer_explanation}
plus outcome pass/fail/skip. No real customer data, no certification claims.

## Out of scope

Real AWS APIs, production incidents, DNSSEC, mutual TLS, performance benchmarks.
