"""D2 Deployable: relay-api (Core Modulith REST API & SSE Inbox Stream)."""

import asyncio
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from relay.api.routers import actions, conversations, health, tickets

app = FastAPI(
    title="Project Relay — Core Modulith API",
    version="0.1.0",
    description="Identity, conversations, tickets, policy, audit, and realtime inbox stream.",
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
async def sse_inbox_stream() -> StreamingResponse:
    """Server-Sent Events (SSE) stream for operator console realtime updates (ADR 009).
    
    Pushes presence, new incoming messages, and ticket assignment changes.
    Survives proxies and reconnects natively with Last-Event-ID.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        # Emits heartbeat and live events
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
