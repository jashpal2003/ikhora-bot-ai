# ADR 009: Server-Sent Events for Operator Realtime and WebSockets for Customer Widget

## Status
Accepted

## Context
The operator console requires realtime streaming updates (inbox state, conversation assignment, presence, and new messages). Realtime bi-directional WebSockets add stateful connection handling, sticky session requirements on Azure Front Door, and proxy reconnect complexity.
The embeddable customer widget, conversely, requires bidirectional, low-latency communication (e.g., interactive typing indicators).

## Decision
We adopt a hybrid streaming strategy:
1. **Operator Console:** Uses **Server-Sent Events (SSE)**.
   - Unidirectional transport (server-to-client) over standard HTTP.
   - Built-in browser reconnection with `Last-Event-ID` header replay.
   - Eliminates WebSocket proxy buffering issues and sticky session requirements.
   - Client actions (message sends, status changes) use standard HTTP `POST` endpoints.
2. **Customer Web Widget:** Uses **WebSockets (WSS)** terminated at `relay-gateway` for bidirectional, low-latency typing indicators and session pings.

## Consequences
- **Positive:** Greatly simplified operator console infrastructure and native compatibility with standard HTTP proxies.
- **Negative:** Two separate realtime transport implementations across operator and customer interfaces.
