"""Policy and authorization models."""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class Principal(BaseModel):
    """The authenticated entity initiating the run or action."""

    type: Literal["human", "agent", "system"]
    id: str
    tenant_id: str
    on_behalf_of: str | None = None  # Enterprise human delegator (e.g. Teams user)
    roles: list[str] = Field(default_factory=list)


class ActionRef(BaseModel):
    """The specific tool or action attempting execution."""

    tool_name: str
    tool_version: str
    side_effect: Literal["read", "write", "external", "destructive", "financial"]


class ResourceRef(BaseModel):
    """The target entity or record being acted upon."""

    system: str  # e.g., "dataverse", "shopify", "graph"
    entity: str  # e.g., "case", "order", "drive_item"
    record_id: str | None = None
    amount: float | None = None


class ApprovalRoute(BaseModel):
    """Routing details when an action requires human sign-off."""

    role: str  # e.g. "support_manager", "compliance"
    sla_minutes: int = 120
    channel: str = "teams"


class Reason(BaseModel):
    code: str
    message: str


class Verdict(BaseModel):
    """The tamper-evident authorization decision.
    
    Can only be legitimately created by policy.authorize().
    Required by tools.invoke().
    """

    decision: Literal["allow", "deny", "require_approval"]
    reasons: list[Reason] = Field(default_factory=list)
    matched_rules: list[str] = Field(default_factory=list)
    approval_route: ApprovalRoute | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    policy_version: str = "v1.0"

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    @property
    def requires_approval(self) -> bool:
        return self.decision == "require_approval"

    @property
    def denied(self) -> bool:
        return self.decision == "deny"
