# ADR 008: Transactional Outbox Pattern with Redis Streams

## Status
Accepted

## Context
Publishing events directly to message brokers during HTTP request processing introduces dual-write inconsistencies (e.g., a ticket is committed to the database, but network failure prevents publishing the event, leaving operators uninformed). Running Apache Kafka prior to product-market fit introduces excessive operational complexity.

## Decision
We implement the **Transactional Outbox Pattern**:
1. Business state changes and their corresponding event records are committed atomically within the same PostgreSQL transaction:
   ```sql
   BEGIN;
   INSERT INTO messages ...;
   INSERT INTO outbox (id, topic, payload, occurred_at) ...;
   COMMIT;
   ```
2. A lightweight outbox processor (using PostgreSQL `LISTEN`/`NOTIFY` or periodic polling) publishes pending events to **Redis Streams**.
3. Redis Streams provides consumer groups, message acknowledgment, at-least-once delivery, and replay windows for traffic volumes below 50k events/sec.

Scale Path: Migrate Redis Streams to Azure Event Hubs (Kafka protocol compatible) if event retention or external streaming demands exceed single-cluster Redis limits.

## Consequences
- **Positive:** Zero dual-write discrepancies and minimal infrastructure maintenance.
- **Negative:** Adds slight publishing latency (~5–50ms) between database commit and event stream consumption.
