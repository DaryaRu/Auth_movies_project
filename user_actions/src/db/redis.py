"""Подключение к Redis."""

import redis.asyncio as redis
from redis.asyncio import Redis as RedisClient

from src.core.config import settings


class Redis:
    """Класс для управления подключением к Redis."""

    redis: RedisClient | None = None

    @classmethod
    def connect(cls) -> None:
        """Подключение к Redis."""
        cls.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
        )

    @classmethod
    def disconnect(cls) -> None:
        """Отключение от Redis."""
        if cls.redis:
            cls.redis.close()

    @classmethod
    def get_client(cls) -> RedisClient | None:
        """Получение клиента Redis."""
        if cls.redis is None:
            cls.connect()
        return cls.redis
