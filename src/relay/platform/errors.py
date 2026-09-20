"""Domain exceptions for Project Relay."""

from typing import Any


class RelayError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TenantContextMissingError(RelayError):
    """Raised when an operation requires tenant context but none is set."""

    def __init__(self, message: str = "Tenant context is required but was not provided.") -> None:
        super().__init__(message)


class PolicyDeniedError(RelayError):
    """Raised when policy evaluation denies an action."""

    def __init__(self, action: str, reasons: list[str]) -> None:
        super().__init__(
            f"Action '{action}' denied by policy: {', '.join(reasons)}",
            {"action": action, "reasons": reasons},
        )


class InsufficientEvidenceError(RelayError):
    """Raised when retrieval yields insufficient evidence to answer a question."""

    def __init__(self, query: str, coverage_gap: str | None = None) -> None:
        super().__init__(
            f"Insufficient evidence for query: {query}",
            {"query": query, "coverage_gap": coverage_gap},
        )


class BudgetExceededError(RelayError):
    """Raised when a workflow or tool call exceeds its allocated budget."""

    def __init__(self, budget_type: str, limit: float, consumed: float) -> None:
        super().__init__(
            f"Budget exceeded for {budget_type}: limit={limit}, consumed={consumed}",
            {"budget_type": budget_type, "limit": limit, "consumed": consumed},
        )


class CircuitBreakerOpenError(RelayError):
    """Raised when a tool's circuit breaker is open due to consecutive failures."""

    def __init__(self, tool_name: str, cooldown_seconds: int) -> None:
        super().__init__(
            f"Circuit breaker is open for tool '{tool_name}'. Cooldown: {cooldown_seconds}s",
            {"tool_name": tool_name, "cooldown_seconds": cooldown_seconds},
        )


class IdempotencyViolationError(RelayError):
    """Raised when an action is retried without a matching or valid idempotency key."""

    def __init__(self, key: str, tool_name: str) -> None:
        super().__init__(
            f"Idempotency violation for tool '{tool_name}' with key '{key}'",
            {"key": key, "tool_name": tool_name},
        )
