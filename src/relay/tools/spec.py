"""Tool specification contracts per §13.1."""

from collections.abc import Callable
from typing import Any, Literal
from pydantic import BaseModel


class ToolSpec(BaseModel):
    """Immutable specification for an executable tool."""

    name: str  # e.g., "dataverse.create_case"
    version: str  # semver, e.g. "1.0.0"
    description: str  # Trusted description authored by team, never by remote MCP
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    side_effect: Literal["read", "write", "external", "destructive", "financial"]
    required_scopes: list[str]
    identity_mode: Literal["obo", "app_only", "tenant_service"]
    idempotent: bool
    timeout_ms: int = 10000
    compensation: str | None = None  # Name of reverse/undo tool
    audit: Literal["full", "hashed", "metadata_only"] = "full"
    handler: Callable[..., Any] | None = None  # Internal execution callable
