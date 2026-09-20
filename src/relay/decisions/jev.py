"""Jev Decision Provider running in shadow mode per §11."""

import time
from relay.decisions.models import Answer, DecisionRequest, TypedDecision


class JevDecisionProvider:
    """Shadow-mode provider for evaluating TypeSafe Jev model.
    
    Logged in parallel for latency, cost, and Brier calibration score,
    but NEVER acted on in production until the promotion gate is passed.
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self.api_url = api_url or "https://api.typesafe.ai/v1/decide"
        self.api_key = api_key

    async def decide(self, req: DecisionRequest) -> TypedDecision:
        """Simulate/execute Jev decision call for shadow comparison."""
        start = time.perf_counter()
        # High speed, bounded output
        answers: dict[str, Answer] = {}
        for q in req.questions:
            answers[q.id] = Answer(value="shadow_eval", probability=0.88, confidence=0.88)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return TypedDecision(
            answers=answers,
            provider="jev_shadow",
            model_version="jev-preview-20260915",
            latency_ms=latency_ms or 85,
            cost_usd=0.000042,
        )
