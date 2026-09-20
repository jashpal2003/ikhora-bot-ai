# ADR 007: Typed Verdict as the Sole Authorization Chokepoint

## Status
Accepted

## Context
Allowing agents to directly invoke tools without centralized policy evaluation risks privilege escalation, unauthorized destructive actions, and compliance violations.

## Decision
All side effects must pass through a single, mandatory policy chokepoint:
```python
def authorize(
    principal: Principal,
    action: ActionRef,
    resource: ResourceRef,
    context: RunContext
) -> Verdict: ...
```
1. `tools.invoke()` requires a strongly-typed `Verdict` object as a required parameter.
2. The `Verdict` object can only be instantiated by `policy.authorize()`.
3. In Phase 1, policies are expressed as declarative, versioned data rules evaluating financial thresholds, customer verification tiers, skill probation periods, and sensitive topics.

## Consequences
- **Positive:** Guarantees that every tool execution is policy-evaluated and recorded in the audit store before execution.
- **Negative:** Requires creating and maintaining declarative rules for every exposed tool capability.
