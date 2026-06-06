"""Redis client module."""

from typing import Optional

from redis.asyncio import Redis

redis: Optional[Redis] = None
