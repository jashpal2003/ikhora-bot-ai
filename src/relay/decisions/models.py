"""Decision models for typed, bounded, and calibrated classifications."""

from typing import Any
from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str
    type: str  # choice, score, bool
    choices: list[str] | None = None
    min_score: int | None = None
    max_score: int | None = None


class Answer(BaseModel):
    value: Any
    probability: float = 1.0
    confidence: float = 1.0


class DecisionRequest(BaseModel):
    state: dict[str, Any]
    questions: list[Question]


class TypedDecision(BaseModel):
    answers: dict[str, Answer]
    provider: str
    model_version: str
    latency_ms: int
    cost_usd: float
    raw_response: dict[str, Any] = Field(default_factory=dict)
