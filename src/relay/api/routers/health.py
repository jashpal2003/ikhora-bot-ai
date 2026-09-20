"""Health and readiness router."""

from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {"status": "healthy", "service": "relay-api", "version": "0.1.0"}
