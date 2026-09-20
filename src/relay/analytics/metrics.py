"""Analytics and OpenTelemetry correlation linkers."""

from typing import Any
from pydantic import BaseModel, Field


class TraceContext(BaseModel):
    """Correlation metadata linking runs, events, and audit logs."""

    trace_id: str
    run_id: str
    tenant_id: str
    action_center_url: str


class CostMetric(BaseModel):
    tenant_id: str
    run_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
