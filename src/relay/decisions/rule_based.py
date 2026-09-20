"""Deterministic rule-based fallback decision provider."""

from relay.decisions.models import Answer, DecisionRequest, TypedDecision


class RuleDecisionProvider:
    """Zero-external-dependency fallback when external decision models fail.
    
    Defaults to conservative actions: human_required = True.
    """

    async def decide(self, req: DecisionRequest) -> TypedDecision:
        """Return safe, deterministic defaults."""
        answers: dict[str, Answer] = {}
        for q in req.questions:
            if q.id == "human_required":
                answers["human_required"] = Answer(value=True, probability=1.0, confidence=1.0)
            elif q.id == "intent":
                answers["intent"] = Answer(value="unknown", probability=1.0, confidence=1.0)
            elif q.id == "priority":
                answers["priority"] = Answer(value="normal", probability=1.0, confidence=1.0)

        return TypedDecision(
            answers=answers,
            provider="rule_fallback",
            model_version="rules-v1",
            latency_ms=1,
            cost_usd=0.0,
        )
