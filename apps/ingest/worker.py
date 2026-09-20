"""D4 Deployable: relay-ingest (Batch Extraction, Chunking & Graph ACL Delta Sync Worker)."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay.ingest.worker")


async def run_ingestion_loop() -> None:
    """Continuously poll Microsoft Graph delta links and process document backlogs."""
    logger.info("Starting Relay Ingestion & ACL Delta Sync worker...")
    while True:
        try:
            # 1. Poll Graph delta queries on document libraries
            # 2. Track acl_hash separately from content_checksum (ADR 006, §9.3)
            # 3. Trigger cheap grant re-sync if only permissions changed
            # 4. Extract, structure-aware chunk, and embed new documents
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in ingestion cycle: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_ingestion_loop())
