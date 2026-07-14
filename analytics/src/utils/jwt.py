import logging
from typing import Any

import httpx
from jose import ExpiredSignatureError, JWTError, jwt
from redis.exceptions import RedisError

from src.core.config import settings
from src.db import redis

logger = logging.getLogger(__name__)

_PUBLIC_KEY_REDIS_KEY = "analytics:public_key"


async def _fetch_public_key() -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.AUTH_API_PUBLIC_KEY_URL, timeout=5)
            if response.status_code != 200:
                logger.error("Failed to fetch public key: status %s", response.status_code)
                return None
            return response.json().get("public_key")
    except Exception as e:
        logger.error("Failed to fetch public key: %s", e)
        return None


async def _cache_public_key(key: str) -> None:
    if redis.redis is None:
        return
    try:
        await redis.redis.set(_PUBLIC_KEY_REDIS_KEY, key, ex=settings.PUBLIC_KEY_CACHE_TTL)
    except RedisError as e:
        logger.warning("Failed to cache public key: %s", e)


async def get_public_key() -> str | None:
    if redis.redis is not None:
        try:
            cached = await redis.redis.get(_PUBLIC_KEY_REDIS_KEY)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        except RedisError as e:
            logger.warning("Redis unavailable, fetching public key from auth-service: %s", e)

    key = await _fetch_public_key()
    if key:
        await _cache_public_key(key)
    return key


async def decode_token(token: str) -> dict[str, Any] | None:
    public_key = await get_public_key()
    if public_key is None:
        return None

    try:
        return jwt.decode(token, public_key, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError:
        return None
    except JWTError:
        if redis.redis is not None:
            await redis.redis.delete(_PUBLIC_KEY_REDIS_KEY)
        public_key = await _fetch_public_key()
        if public_key is None:
            return None
        await _cache_public_key(public_key)
        try:
            return jwt.decode(token, public_key, algorithms=[settings.JWT_ALGORITHM])
        except JWTError as e:
            logger.error("Failed to decode token: %s", e)
            return None
