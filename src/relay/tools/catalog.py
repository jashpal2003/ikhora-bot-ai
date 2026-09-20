"""Standard certified tool specifications for Project Relay (P0 & P1)."""

from typing import Any, Literal
from pydantic import BaseModel, Field
from relay.tools.spec import ToolSpec


# --- Dataverse Schemas ---
class CreateCaseInput(BaseModel):
    title: str
    customer_id: str
    description: str | None = None


class CreateCaseOutput(BaseModel):
    case_id: str
    status: str
    created_in_dataverse: bool = True


class GetCaseInput(BaseModel):
    case_id: str


class GetCaseOutput(BaseModel):
    case_id: str
    title: str
    status: str


# --- Shopify Schemas ---
class GetOrderInput(BaseModel):
    order_id: str


class GetOrderOutput(BaseModel):
    order_id: str
    financial_status: str
    fulfillment_status: str
    total_price: str
    currency: str = "USD"


class RefundCreateInput(BaseModel):
    order_id: str
    amount: float
    reason: str | None = None


class RefundCreateOutput(BaseModel):
    refund_id: str
    amount: float
    status: str


# --- Graph Schemas ---
class SearchDocsInput(BaseModel):
    query: str


class SearchDocsOutput(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)


# --- Internal Schemas ---
class CreateTicketInput(BaseModel):
    title: str
    priority: str = "normal"
    conversation_id: str | None = None


class CreateTicketOutput(BaseModel):
    ticket_id: str
    status: str


# Tool Specs Catalog
DATAVERSE_CREATE_CASE = ToolSpec(
    name="dataverse.create_case",
    version="1.0.0",
    description="Create a customer support case in Microsoft Dataverse.",
    input_schema=CreateCaseInput,
    output_schema=CreateCaseOutput,
    side_effect="write",
    required_scopes=["Cases.Write"],
    identity_mode="obo",
    idempotent=True,
    timeout_ms=10000,
    compensation="dataverse.cancel_case",
    audit="full",
)

DATAVERSE_GET_CASE = ToolSpec(
    name="dataverse.get_case",
    version="1.0.0",
    description="Fetch live case details from Microsoft Dataverse.",
    input_schema=GetCaseInput,
    output_schema=GetCaseOutput,
    side_effect="read",
    required_scopes=["Cases.Read"],
    identity_mode="obo",
    idempotent=True,
    timeout_ms=5000,
    audit="metadata_only",
)

SHOPIFY_GET_ORDER = ToolSpec(
    name="shopify.get_order",
    version="1.0.0",
    description="Fetch live order status and shipping tracking from Shopify.",
    input_schema=GetOrderInput,
    output_schema=GetOrderOutput,
    side_effect="read",
    required_scopes=["read_orders"],
    identity_mode="tenant_service",
    idempotent=True,
    timeout_ms=5000,
    audit="metadata_only",
)

SHOPIFY_REFUND_CREATE = ToolSpec(
    name="shopify.refund_create",
    version="1.0.0",
    description="Issue a financial refund for an order in Shopify.",
    input_schema=RefundCreateInput,
    output_schema=RefundCreateOutput,
    side_effect="financial",
    required_scopes=["write_orders"],
    identity_mode="tenant_service",
    idempotent=True,
    timeout_ms=10000,
    compensation="shopify.refund_reverse",
    audit="full",
)

GRAPH_SEARCH_DOCS = ToolSpec(
    name="graph.search_docs",
    version="1.0.0",
    description="Search enterprise SharePoint and OneDrive documents via Microsoft Graph.",
    input_schema=SearchDocsInput,
    output_schema=SearchDocsOutput,
    side_effect="read",
    required_scopes=["Files.Read.All"],
    identity_mode="obo",
    idempotent=True,
    timeout_ms=8000,
    audit="metadata_only",
)

INTERNAL_CREATE_TICKET = ToolSpec(
    name="internal.create_ticket",
    version="1.0.0",
    description="Create an internal escalation ticket for human support operators.",
    input_schema=CreateTicketInput,
    output_schema=CreateTicketOutput,
    side_effect="write",
    required_scopes=["Tickets.Write"],
    identity_mode="tenant_service",
    idempotent=True,
    timeout_ms=3000,
    audit="full",
)

ALL_CERTIFIED_TOOLS = [
    DATAVERSE_CREATE_CASE,
    DATAVERSE_GET_CASE,
    SHOPIFY_GET_ORDER,
    SHOPIFY_REFUND_CREATE,
    GRAPH_SEARCH_DOCS,
    INTERNAL_CREATE_TICKET,
]


def get_default_registry() -> Any:
    """Return a ToolRegistry pre-populated with all certified tool specs."""
    from relay.tools.registry import ToolRegistry
    registry = ToolRegistry()
    for spec in ALL_CERTIFIED_TOOLS:
        registry.register(spec)
    return registry
