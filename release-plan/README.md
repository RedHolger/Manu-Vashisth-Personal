# ReleasePlan — release management against real history

Manage a release with evidence instead of checkboxes: a charter with a frozen
baseline separated from scope changes, readiness computed from artifact
existence (a missing artifact can never read "ready"), solo coordination
recorded honestly as solo, and a retrospective with a runnable planning gate.
The subject is real — this portfolio's own review-bundle release, validated
against its git history. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 156 tests
```

Recorded: charter re-checks real commits; destructive demos run in temp dirs;
the preflight gate correctly fails on withheld work and tracked build output.
History-dependent checks skip with explicit reasons outside a full-history
checkout.

## Limits

A solo case study: honest solo bookkeeping, not cross-functional leadership.
Retrospective, not live release management.
