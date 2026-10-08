# FlowLedger — durable job execution

Accept a job once, attempt it at-least-once, and let every logical side
effect happen exactly once — under a mock downstream contract, with
crash-tested boundaries. Java 21, Spring Boot 3.4, PostgreSQL 16.

## How it works

- `POST /jobs` submits idempotently; `GET /jobs/{id}` reads state.
- An outbox table + relay delivers attempts; worker leases with generation
  fencing so stale workers cannot double-apply.
- Retries are bounded; validation rejects bad payloads with 400s; conflicts
  surface as 409.

## Run it (needs Docker)

```sh
docker compose up -d        # PostgreSQL 16
mvn test                    # 22 tests: contract, idempotency, crash windows
```

Recorded outcomes: 22/22 unit tests; 40/40 live-crash assertions across
effect-before-ack / fencing / consumer-before-dispatch; steady load with
baseline p50 ~250 ms. Single-machine figures, not capacity claims.

## Limits

At-least-once attempts with deduplicated effects *under the mock downstream
contract* — not exactly-once for arbitrary services. Idempotency hashes the
controller's serialized payload (key order significant). No production
deployment; acceptance review pending.
