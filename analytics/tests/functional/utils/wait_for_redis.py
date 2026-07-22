"""Script that waits for Redis service to start."""

import asyncio
import logging

from redis.asyncio import Redis

from analytics.tests.settings import test_settings


async def wait_for_redis() -> None:
    """Ping Redis until responds or raise RuntimeError after max_attempts."""
    host = test_settings.redis_host
    port = test_settings.redis_port
    max_attempts = test_settings.service_wait_max_attempts
    delay = test_settings.service_wait_delay
    client = Redis(host=host, port=port)
    for attempt in range(1, max_attempts + 1):
        if await client.ping():
            await client.aclose()
            return
        logging.warning(
            "Redis not ready, attempt %d/%d", attempt, max_attempts
        )
        await asyncio.sleep(delay)
    await client.aclose()
    raise RuntimeError(
        f"Redis at {host}:{port} not available after {max_attempts} attempts"
    )


if __name__ == "__main__":
    asyncio.run(wait_for_redis())
