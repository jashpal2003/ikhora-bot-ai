"""D3 Deployable: relay-agent (Temporal Durable Workflow Worker)."""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from relay.agent.activities import (
    authorize_activity,
    classify_intent_activity,
    create_handoff_packet_activity,
    execute_tool_activity,
    plan_next_step_activity,
    send_reply_activity,
)
from relay.agent.workflow import AgentRunWorkflow
from relay.platform.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay.agent.worker")


async def run_worker() -> None:
    """Connect to Temporal and start processing workflow and activity tasks."""
    logger.info(f"Connecting to Temporal at {settings.temporal_host}...")
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AgentRunWorkflow],
        activities=[
            classify_intent_activity,
            plan_next_step_activity,
            authorize_activity,
            execute_tool_activity,
            send_reply_activity,
            create_handoff_packet_activity,
        ],
    )

    logger.info(f"Relay Agent Worker running on queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
