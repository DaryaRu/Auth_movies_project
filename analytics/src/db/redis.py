import logging
from typing import Optional

from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

redis: Optional[Redis] = None


class FaultTolerantRedisBackend(RedisBackend):
    async def get_with_ttl(self, key: str) -> tuple[int, str]:
        try:
            return await super().get_with_ttl(key)
        except RedisError as e:
            logger.warning("Redis unavailable, cache miss: %s (%s)", key, e)
            return 0, None

    async def set(self, key: str, value: str, expire: int = None):
        try:
            await super().set(key, value, expire)
        except RedisError as e:
            logger.warning("Redis unavailable, skip set: %s (%s)", key, e)
