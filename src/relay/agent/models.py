"""Agent runtime models and workflow context."""

from typing import Any, Literal
from pydantic import BaseModel, Field

from relay.policy.budgets import Budget


class PlanStep(BaseModel):
    """Next action decided by the planner activity."""

    kind: Literal["respond", "handoff", "tool_call"]
    message: str | None = None
    handoff_reason: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    cost_estimate: float = 0.0005


class RunOutcome(BaseModel):
    """Final outcome of an AgentRunWorkflow."""

    status: Literal["completed", "handed_off", "rejected", "failed"]
    reply_text: str | None = None
    handoff_reason: str | None = None
    steps_taken: int = 0
    total_cost_usd: float = 0.0

    @classmethod
    def completed(cls, reply_text: str, steps: int = 1, cost: float = 0.0) -> "RunOutcome":
        return cls(status="completed", reply_text=reply_text, steps_taken=steps, total_cost_usd=cost)

    @classmethod
    def handed_off(cls, reason: str, steps: int = 1, cost: float = 0.0) -> "RunOutcome":
        return cls(status="handed_off", handoff_reason=reason, steps_taken=steps, total_cost_usd=cost)

    @classmethod
    def rejected(cls, steps: int = 1, cost: float = 0.0) -> "RunOutcome":
        return cls(status="rejected", handoff_reason="approval_rejected", steps_taken=steps, total_cost_usd=cost)


class RunContext(BaseModel):
    """Context passed into an AgentRunWorkflow."""

    run_id: str
    tenant_id: str
    conversation_id: str
    contact_id: str | None = None
    channel: str
    user_message: str
    identity_tier: str = "anonymous"
    on_behalf_of: str | None = None
    trace_id: str
    budget: Budget = Field(default_factory=Budget)
    state: dict[str, Any] = Field(default_factory=dict)
