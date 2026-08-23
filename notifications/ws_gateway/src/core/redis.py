"""Redis-клиент (синглтон)."""

import redis.asyncio as aioredis

from src.core.config import settings

redis: aioredis.Redis | None = None


def init() -> None:
    """Инициализировать Redis-клиент."""
    global redis
    redis = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False,
    )


async def close() -> None:
    """Закрыть Redis-клиент."""
    global redis
    if redis is not None:
        await redis.close()
        redis = None