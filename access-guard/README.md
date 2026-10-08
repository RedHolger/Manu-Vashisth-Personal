# AccessGuard — authorization testing with an independent oracle

Find cross-tenant and object-ownership bugs the way they should be found:
a trusted policy oracle, written independently of the app, judging a real
loopback HTTP service over 22 cases. The vulnerable variant is caught
(7 mismatches: cross-tenant, ownership, expired/revoked admin replay); the
repaired variant is clean (0/22). A CI gate drives before/after with the
oracle hash-guarded, and a threat model states what finite cases cannot
prove. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 40 tests
```

Recorded: expired/revoked sessions fail closed; privilege demotion removes
reach (roles from server state, never token claims); reports carry no bearer
values. Live integration against real services needs Docker/Postgres and is
not attempted here.

## Limits

22-case lab matrix, 4 planted bug classes — counts, not rates, and not a
security proof. Sequential single-client HTTP on loopback; no concurrency,
network-position, or brute-force coverage.
