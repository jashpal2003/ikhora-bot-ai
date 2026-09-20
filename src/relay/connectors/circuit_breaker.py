"""Per-(tenant, tool) Circuit Breaker per §10.1."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from relay.platform.errors import CircuitBreakerOpenError


@dataclass
class BreakerState:
    failures: list[float] = field(default_factory=list)  # timestamps of failures
    opened_at: float | None = None
    is_open: bool = False


class CircuitBreakerRegistry:
    """Manages circuit breaker states for (tenant_id, tool_name) pairs.
    
    Rule: 5 failures within 60s -> OPEN for 300s (5 minutes).
    """

    def __init__(self, failure_threshold: int = 5, window_seconds: int = 60, cooldown_seconds: int = 300) -> None:
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[tuple[str, str], BreakerState] = defaultdict(BreakerState)

    def check_tool_available(self, tenant_id: str, tool_name: str) -> None:
        """Check if tool is available; raise CircuitBreakerOpenError if open."""
        key = (tenant_id, tool_name)
        state = self._states[key]
        now = time.time()

        if state.is_open:
            if state.opened_at and (now - state.opened_at) >= self.cooldown_seconds:
                # Cooldown period elapsed -> Half-open / reset
                state.is_open = False
                state.opened_at = None
                state.failures.clear()
            else:
                remaining = int(self.cooldown_seconds - (now - (state.opened_at or now)))
                raise CircuitBreakerOpenError(tool_name, max(1, remaining))

    def record_success(self, tenant_id: str, tool_name: str) -> None:
        """Clear failure count on successful execution."""
        key = (tenant_id, tool_name)
        state = self._states[key]
        state.failures.clear()
        state.is_open = False

    def record_failure(self, tenant_id: str, tool_name: str) -> bool:
        """Record a failure; if 5 failures in 60s, open breaker for 5 mins."""
        key = (tenant_id, tool_name)
        state = self._states[key]
        now = time.time()

        # Evict failures outside rolling window
        state.failures = [t for t in state.failures if (now - t) <= self.window_seconds]
        state.failures.append(now)

        if len(state.failures) >= self.failure_threshold:
            state.is_open = True
            state.opened_at = now
            return True  # Tripped open
        return False

    def force_kill_switch(self, tenant_id: str, tool_name: str) -> None:
        """Manually trip circuit breaker (admin kill switch)."""
        key = (tenant_id, tool_name)
        state = self._states[key]
        state.is_open = True
        state.opened_at = time.time()


# Singleton registry instance
circuit_breaker = CircuitBreakerRegistry()
