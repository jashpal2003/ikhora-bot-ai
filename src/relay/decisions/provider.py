"""DecisionProvider protocol per §11.2."""

from typing import Protocol
from relay.decisions.models import DecisionRequest, TypedDecision


class DecisionProvider(Protocol):
    """Abstract interface for bounded decision generation."""

    async def decide(self, req: DecisionRequest) -> TypedDecision:
        """Produce a calibrated, typed decision based on unstructured state."""
        ...
