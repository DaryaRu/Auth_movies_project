"""Redis client and fault-tolerant cache backend."""

import logging
from typing import Optional

from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

redis: Optional[Redis] = None


class FaultTolerantRedisBackend(RedisBackend):
    """Redis backend that treats connection errors as cache misses.

    Без этого класса RedisError при недоступном Redis не перехватывается
    и запрос падает с 500. FaultTolerantRedisBackend обеспечивает
    graceful degradation: API продолжает работать, только без кэша.

    Сценарий при недоступном Redis:
      @cache вызывает get_with_ttl() → RedisError перехвачен → (0, None)
      → @cache видит cache miss → запрос идёт в обработчик → ES
      → ответ клиенту 200
      → @cache вызывает set() → RedisError перехвачен
        → пользователь не видит сбоя
    """

    async def get_with_ttl(self, key: str) -> tuple[int, str]:
        try:
            return await super().get_with_ttl(key)
        except RedisError as e:
            logger.warning("Redis unavailable, cache miss: %s (%s)", key, e)
            # (0, None) — сигнал cache miss для @cache декоратора
            return 0, None

    async def set(self, key: str, value: str, expire: int = None):
        try:
            await super().set(key, value, expire)
        except RedisError as e:
            logger.warning("Redis unavailable, skip set: %s (%s)", key, e)
