"""Run collectors and ingest listings into storage."""
from __future__ import annotations

import asyncio
import logging

from immotogo.collectors.sites import collect_all
from immotogo.config import get_settings
from immotogo.pipeline.ingest import ingest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    logger.info("Starting collection with concurrency=%s", settings.crawl_concurrency)
    listings = await collect_all(concurrency=settings.crawl_concurrency)
    logger.info("Fetched %s listings", len(listings))
    chunk_ids = ingest(listings)
    logger.info("Indexed %s chunks", len(chunk_ids))


if __name__ == "__main__":
    asyncio.run(main())
