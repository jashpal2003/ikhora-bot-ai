"""D1 Deployable: relay-gateway (Stateless Channel Ingress & Webhook Receiver)."""

import json
from contextlib import asynccontextmanager
from typing import Any
import redis.asyncio as aioredis
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from relay.channels.whatsapp.adapter import WhatsAppAdapter
from relay.platform.config import settings

# Redis client for deduplication and raw stream persistence
redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        redis_client = None
    yield
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="Project Relay — Channel Gateway",
    version="0.1.0",
    description="Stateless channel webhook ingress, signature verification, raw event persistence, ACK <200ms.",
    lifespan=lifespan,
)

whatsapp_adapter = WhatsAppAdapter(app_secret=settings.whatsapp_app_secret)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "healthy", "service": "relay-gateway", "version": "0.1.0"}


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
    x_tenant_id: str = Header("default_tenant", alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Ingest WhatsApp Cloud API webhooks with HMAC-SHA256 signature verification.
    
    Must acknowledge in <200ms to prevent Meta from marking the webhook unhealthy.
    Enforces 24h deduplication in Redis (P4, §14.3).
    """
    raw_body = await request.body()

    # 1. Verify HMAC-SHA256 signature
    if not whatsapp_adapter.verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: dict[str, Any] = await request.json()

    # Extract message ID for deduplication
    entry = payload.get("entry", [{}])[0]
    change = entry.get("changes", [{}])[0]
    messages = change.get("value", {}).get("messages", [])
    if not messages:
        return {"status": "acknowledged_status_update"}

    message_id = messages[0].get("id", "")

    # 2. Redis 24h window deduplication (P4)
    if redis_client and message_id:
        dedupe_key = f"relay:dedupe:whatsapp:{message_id}"
        is_new = await redis_client.set(dedupe_key, "1", nx=True, ex=86400)
        if not is_new:
            return {"status": "duplicate_ignored", "message_id": message_id}

    # 3. Normalize into ChannelMessageEnvelope
    envelope = whatsapp_adapter.normalize_inbound(payload, tenant_id=x_tenant_id)

    # 4. Push to Redis stream for durable agent consumption
    if redis_client:
        await redis_client.xadd(
            "relay:stream:inbound",
            {"payload": json.dumps(envelope.model_dump(mode="json"))},
        )

    return {"status": "accepted", "message_id": message_id}


@app.post("/webhooks/teams")
async def receive_teams_webhook(
    request: Request,
    x_tenant_id: str = Header("default_tenant", alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Ingest Microsoft Teams activity payloads forwarded by apps/teams-adapter."""
    payload: dict[str, Any] = await request.json()
    activity_id = payload.get("id", "")

    if redis_client and activity_id:
        is_new = await redis_client.set(f"relay:dedupe:teams:{activity_id}", "1", nx=True, ex=86400)
        if not is_new:
            return {"status": "duplicate_ignored"}

    return {"status": "accepted", "activity_id": activity_id}


@app.websocket("/ws/widget/{session_id}")
async def widget_websocket(websocket: WebSocket, session_id: str) -> None:
    """Terminate customer widget WebSockets for low-latency chat and typing indicators (ADR 009)."""
    await websocket.accept()
    try:
        await websocket.send_json({"type": "ready", "session_id": session_id})
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "typing":
                # Broadcast typing indicator
                await websocket.send_json({"type": "typing_ack"})
            elif msg_type == "message":
                text_content = data.get("text", "")
                await websocket.send_json({
                    "type": "message_ack",
                    "text": text_content,
                    "reply": "Thank you for contacting support. An agent or operator will assist you shortly.",
                })
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.gateway.main:app", host="0.0.0.0", port=8001, reload=True)
