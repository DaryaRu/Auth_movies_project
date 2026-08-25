"""Подключение к Redis."""

import redis.asyncio as aioredis
from redis.asyncio import Redis as RedisClient

from src.core.config import settings


class Redis:
    """Класс для управления подключением к Redis."""

    redis: RedisClient | None = None

    @classmethod
    async def connect(cls) -> None:
        """Подключение к Redis."""
        cls.redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=False,
        )

    @classmethod
    async def disconnect(cls) -> None:
        """Отключение от Redis."""
        if cls.redis is not None:
            await cls.redis.close()
            cls.redis = None
