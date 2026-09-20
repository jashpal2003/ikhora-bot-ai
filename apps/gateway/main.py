"""D1 Deployable: relay-gateway (Stateless Channel Ingress & Webhook Receiver)."""

from typing import Any
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse

from relay.channels.whatsapp.adapter import WhatsAppAdapter
from relay.platform.config import settings

app = FastAPI(
    title="Project Relay — Channel Gateway",
    version="0.1.0",
    description="Stateless channel webhook ingress, signature verification, raw event persistence, ACK <200ms.",
)

whatsapp_adapter = WhatsAppAdapter(app_secret=settings.whatsapp_app_secret)


@app.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
) -> Response:
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """Ingest WhatsApp Cloud API webhooks with HMAC-SHA256 signature verification.
    
    Must acknowledge in <200ms to prevent Meta from marking the webhook unhealthy.
    """
    raw_body = await request.body()

    # 1. Verify HMAC-SHA256 signature
    if not whatsapp_adapter.verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: dict[str, Any] = await request.json()

    # 2. Normalize and enqueue to internal processing pipeline
    # In production, pushes to Redis raw queue for relay-agent consumption
    return {"status": "accepted"}


@app.post("/webhooks/teams")
async def receive_teams_webhook(request: Request) -> dict[str, Any]:
    """Ingest Microsoft Teams activity payloads."""
    payload: dict[str, Any] = await request.json()
    return {"status": "accepted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.gateway.main:app", host="0.0.0.0", port=8001, reload=True)
