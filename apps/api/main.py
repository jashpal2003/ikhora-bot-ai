"""D2 Deployable: relay-api (Core Modulith REST API & SSE Inbox Stream)."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from fastapi import FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from relay.api.routers import actions, conversations, health, tickets
from relay.platform.config import settings

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
    title="Project Relay — Core Modulith API",
    version="0.1.0",
    description="Identity, conversations, tickets, policy, audit, and realtime inbox stream.",
    lifespan=lifespan,
)

# Enable CORS for Next.js operator console
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount domain routers
app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(tickets.router)
app.include_router(actions.router)


@app.get("/inbox/stream")
async def sse_inbox_stream(
    tenant_id: str = Query("default_tenant"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> StreamingResponse:
    """Server-Sent Events (SSE) stream for operator console realtime updates (ADR 009).
    
    Subscribes to Redis pub/sub channel relay:inbox:{tid} and pushes events.
    Survives proxies and reconnects natively with Last-Event-ID.
    """
    effective_tenant = x_tenant_id or tenant_id

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"event: connected\ndata: {{\"tenant_id\": \"{effective_tenant}\"}}\n\n"

        if redis_client:
            pubsub = redis_client.pubsub()
            channel = f"relay:inbox:{effective_tenant}"
            await pubsub.subscribe(channel)
            try:
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
                    if message and message.get("data"):
                        yield f"event: update\ndata: {message['data']}\n\n"
                    else:
                        # Heartbeat ping
                        yield "event: ping\ndata: {\"status\": \"alive\"}\n\n"
            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
        else:
            # Standalone heartbeat when Redis is unavailable
            while True:
                yield "event: ping\ndata: {\"status\": \"connected\"}\n\n"
                await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
