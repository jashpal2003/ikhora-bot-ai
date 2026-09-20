"""Per-run and per-tenant budget evaluation."""

from pydantic import BaseModel
from relay.platform.errors import BudgetExceededError


class Budget(BaseModel):
    """Resource budget ceilings for an agent run."""

    steps: int = 12
    wall_ms: int = 90000
    usd: float = 0.50
    tool_calls: int = 8


class BudgetLedger(BaseModel):
    """Tracks consumption against an allocated budget."""

    consumed_steps: int = 0
    consumed_wall_ms: int = 0
    consumed_usd: float = 0.0
    consumed_tool_calls: int = 0

    def consume_step(self, cost_estimate: float = 0.0, is_tool_call: bool = False, is_destructive: bool = False) -> None:
        """Increment consumption counters."""
        self.consumed_steps += 1
        self.consumed_usd += cost_estimate
        if is_tool_call:
            # Destructive tools count triple per §10.1
            weight = 3 if is_destructive else 1
            self.consumed_tool_calls += weight

    def check_exhausted(self, budget: Budget) -> tuple[bool, str | None]:
        """Check if any budget dimension has been exceeded."""
        if self.consumed_steps >= budget.steps:
            return True, f"step_budget_exhausted ({self.consumed_steps}/{budget.steps})"
        if self.consumed_usd >= budget.usd:
            return True, f"cost_budget_exhausted (${self.consumed_usd:.4f}/${budget.usd:.2f})"
        if self.consumed_tool_calls >= budget.tool_calls:
            return True, f"tool_budget_exhausted ({self.consumed_tool_calls}/{budget.tool_calls})"
        return False, None

    def assert_within_budget(self, budget: Budget) -> None:
        """Raise BudgetExceededError if limits are breached."""
        exhausted, reason = self.check_exhausted(budget)
        if exhausted:
            raise BudgetExceededError(reason or "budget", 0, 0)
