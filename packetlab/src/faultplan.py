"""Bounded fault-plan descriptors. Plans are validated DATA; execution needs a
live topology and is UNRUN in this environment."""
from dataclasses import dataclass, field

KINDS = ("link-down", "peer-shutdown", "wrong-route")
MAX_DURATION_S = 300


@dataclass
class FaultPlan:
    target: str
    kind: str
    max_duration_s: int
    affected_prefixes: list[str] = field(default_factory=list)
    rollback: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)


def validate(plan: FaultPlan) -> list[str]:
    errors: list[str] = []
    if plan.kind not in KINDS:
        errors.append(f"unknown kind {plan.kind!r}; want one of {KINDS}")
    if not plan.target:
        errors.append("empty target")
    if not (0 < plan.max_duration_s <= MAX_DURATION_S):
        errors.append(f"max_duration_s must be 1..{MAX_DURATION_S}")
    if not plan.rollback:
        errors.append("missing rollback steps (cleanup is mandatory)")
    if "peers-established" not in plan.preconditions:
        errors.append("missing precondition: peers-established before start")
    if plan.kind == "wrong-route" and not plan.affected_prefixes:
        errors.append("wrong-route needs affected_prefixes to watch")
    return errors
