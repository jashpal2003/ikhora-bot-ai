# ADR 003: Temporal for Durable Agent Execution

## Status
Accepted

## Context
Agent executions involve multi-step reasoning, external API calls, step/cost budget constraints, circuit breakers, and long-lived human approval pauses (e.g., manager sign-off on refunds > $50).
Building a custom database state machine with polling entails thousands of lines of fragile boilerplate, race conditions, deployment unreliability, and lost in-flight runs.

## Decision
We adopt **Temporal** as the durable execution engine for the agent runtime (`relay-agent`):
1. The agent loop is defined as a Temporal workflow (`AgentRunWorkflow`).
2. Long-lived human approvals are modeled as workflow signal waits:
   `await workflow.wait_condition(lambda: self._approval is not None, timeout=timedelta(hours=48))`
3. Automatic retries, activity timeouts, budget exhaustion handoffs, and deterministic history replays are handled natively by Temporal.

## Consequences
- **Positive:** Out-of-the-box support for long-running pauses, guaranteed execution durability, zero dropped runs across deployments, and native trace replay for evaluations.
- **Negative:** Requires team adherence to Temporal determinism constraints (no raw I/O or non-deterministic functions in workflow code).
