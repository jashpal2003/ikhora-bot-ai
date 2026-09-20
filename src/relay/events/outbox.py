"""Transactional Outbox Pattern implementation with Redis Streams publisher."""

import json
from typing import Any
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.events.envelope import EventEnvelope
from relay.platform.ids import generate_id


class OutboxWriter:
    """Writes domain events to the outbox table within the same transaction."""

    @staticmethod
    async def record_event(session: AsyncSession, envelope: EventEnvelope) -> str:
        """Insert an event envelope into the transactional outbox table."""
        outbox_id = generate_id("outbox")
        payload = envelope.model_dump(mode="json")

        await session.execute(
            text("""
                INSERT INTO outbox (id, tenant_id, topic, payload, occurred_at)
                VALUES (:id, :tenant_id, :topic, :payload, :occurred_at)
            """),
            {
                "id": outbox_id,
                "tenant_id": envelope.tenant_id,
                "topic": envelope.event_type,
                "payload": json.dumps(payload),
                "occurred_at": envelope.occurred_at,
            },
        )
        return outbox_id


class OutboxPublisher:
    """Reads pending events from the outbox and publishes them to Redis Streams."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def publish_batch(self, session: AsyncSession, limit: int = 100) -> int:
        """Fetch uncommitted outbox rows, publish to Redis stream, and mark processed."""
        result = await session.execute(
            text("""
                SELECT id, tenant_id, topic, payload 
                FROM outbox 
                WHERE processed_at IS NULL 
                ORDER BY occurred_at ASC 
                LIMIT :limit 
                FOR UPDATE SKIP LOCKED
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
        if not rows:
            return 0

        published_ids = []
        for row in rows:
            stream_name = f"relay:events:{row.topic}"
            await self.redis.xadd(
                stream_name,
                {"tenant_id": row.tenant_id, "payload": row.payload},
            )
            published_ids.append(row.id)

        await session.execute(
            text("""
                UPDATE outbox 
                SET processed_at = now() 
                WHERE id = ANY(:ids)
            """),
            {"ids": published_ids},
        )
        await session.commit()
        return len(published_ids)
