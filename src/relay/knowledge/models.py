"""Knowledge models, Evidence, and EvidencePack definitions."""

from typing import Literal
from pydantic import BaseModel, Field


class ConflictPair(BaseModel):
    """Pair of semantically contradictory evidence chunks."""

    source_a_title: str
    source_a_claim: str
    source_b_title: str
    source_b_claim: str
    divergence_summary: str


class Evidence(BaseModel):
    """A single piece of retrieved knowledge grounding an agent claim."""

    chunk_id: str
    document_id: str
    document_title: str
    deep_link: str | None = None
    text: str
    relevance: float
    freshness_days: int
    source_trust: float = 1.0
    version: str = "1.0"


class EvidencePack(BaseModel):
    """The structured output of the 3-layer ACL-aware retrieval engine."""

    items: list[Evidence] = Field(default_factory=list)
    sufficiency: Literal["sufficient", "weak", "insufficient"]
    conflicts: list[ConflictPair] = Field(default_factory=list)
    coverage_gap: str | None = None
