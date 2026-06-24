"""Script that waits for Elasticsearch service to start."""

import asyncio
import logging

from elasticsearch import AsyncElasticsearch

from functional.settings import test_settings


async def wait_for_es() -> None:
    """Ping ES until responds or raise RuntimeError after max_attempts."""
    host = f"http://{test_settings.elastic_host}:{test_settings.elastic_port}"
    max_attempts = test_settings.service_wait_max_attempts
    delay = test_settings.service_wait_delay
    client = AsyncElasticsearch(hosts=[host])
    for attempt in range(1, max_attempts + 1):
        if await client.ping():
            await client.close()
            return
        logging.warning(
            "Elasticsearch not ready, attempt %d/%d", attempt, max_attempts
        )
        await asyncio.sleep(delay)
    await client.close()
    raise RuntimeError(
        f"Elasticsearch at {host} not available after {max_attempts} attempts"
    )


if __name__ == "__main__":
    asyncio.run(wait_for_es())
