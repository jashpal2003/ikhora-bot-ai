"""Hard router distinguishing knowledge from live state (P5, §10.2)."""

import re
from typing import Literal
from pydantic import BaseModel, Field


class EntityRef(BaseModel):
    entity_type: str  # e.g. "order_id", "case_id", "ticket_id"
    value: str


class QueryRoute(BaseModel):
    """Routing specification produced before retrieval or action."""

    kind: Literal["knowledge", "live_state", "mixed", "action", "chitchat"]
    live_entities: list[EntityRef] = Field(default_factory=list)
    knowledge_topics: list[str] = Field(default_factory=list)

    @property
    def requires_live_state(self) -> bool:
        return self.kind in ("live_state", "mixed")

    @property
    def requires_knowledge(self) -> bool:
        return self.kind in ("knowledge", "mixed")


class QueryClassifier:
    """Hard-routes user messages by intent.
    
    Crucial Invariant: If kind == 'live_state', answering from RAG is structurally FORBIDDEN.
    """

    @classmethod
    def route_query(cls, text: str) -> QueryRoute:
        lower = text.lower()
        live_entities: list[EntityRef] = []

        # Detect order reference e.g. #8281 or order 8281
        order_match = re.search(r"(?:order|#)\s*([0-9]{3,8})", lower)
        if order_match:
            live_entities.append(EntityRef(entity_type="order_id", value=order_match.group(1)))

        # Detect case reference e.g. CAS-4471
        case_match = re.search(r"cas-([0-9a-zA-Z]{4,8})", lower)
        if case_match:
            live_entities.append(EntityRef(entity_type="case_id", value=case_match.group(0).upper()))

        # Live state questions
        is_live_query = any(k in lower for k in ["where is my", "order status", "track package", "delivery time", "balance", "track order"])
        # Knowledge questions
        is_knowledge_query = any(k in lower for k in ["policy", "return", "refund policy", "terms", "warranty", "guidelines", "how do i"])

        if live_entities or is_live_query:
            if is_knowledge_query:
                return QueryRoute(kind="mixed", live_entities=live_entities, knowledge_topics=["returns", "orders"])
            return QueryRoute(kind="live_state", live_entities=live_entities)

        if is_knowledge_query:
            topics = []
            if "refund" in lower or "return" in lower:
                topics.append("refund_policy")
            if "warranty" in lower:
                topics.append("warranty")
            if "legal" in lower or "compliance" in lower:
                topics.append("legal")
            return QueryRoute(kind="knowledge", knowledge_topics=topics)

        # Action requests
        if any(k in lower for k in ["cancel my", "refund me", "open a case", "file claim"]):
            return QueryRoute(kind="action", live_entities=live_entities)

        return QueryRoute(kind="chitchat")
