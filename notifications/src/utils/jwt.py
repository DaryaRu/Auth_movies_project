"""JWT-декодирование с кэшированием публичного ключа auth-service в Redis."""

import logging
from typing import Any

import httpx
from jose import ExpiredSignatureError, JWTError, jwt

from src.core.config import settings
from src.db.redis import Redis

logger = logging.getLogger(__name__)

_PUBLIC_KEY_REDIS_KEY = "notifications:public_key"
_PUBLIC_KEY_TTL = 3600


async def _fetch_public_key() -> str | None:
    """Получить публичный ключ от auth-сервиса."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                settings.AUTH_API_PUBLIC_KEY_URL, timeout=5
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch public key: status %s",
                    response.status_code,
                )
                return None
            return response.json().get("public_key")
    except Exception as e:
        logger.error("Failed to fetch public key: %s", e)
        return None


async def _cache_public_key(key: str) -> None:
    if Redis.redis is not None:
        await Redis.redis.set(_PUBLIC_KEY_REDIS_KEY, key, ex=_PUBLIC_KEY_TTL)


async def get_public_key() -> str | None:
    """Вернуть публичный ключ из кэша Redis или от auth-сервиса."""
    if Redis.redis is not None:
        cached = await Redis.redis.get(_PUBLIC_KEY_REDIS_KEY)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached

    key = await _fetch_public_key()
    if key:
        await _cache_public_key(key)
    return key


async def decode_token(token: str) -> dict[str, Any] | None:
    """Декодировать JWT-токен.

    При ошибке подписи сбрасывает кэш ключа и повторяет попытку.
    """
    public_key = await get_public_key()
    if public_key is None:
        return None

    try:
        return jwt.decode(
            token, public_key, algorithms=[settings.JWT_ALGORITHM]
        )
    except ExpiredSignatureError:
        return None
    except JWTError:
        if Redis.redis is not None:
            await Redis.redis.delete(_PUBLIC_KEY_REDIS_KEY)
        public_key = await _fetch_public_key()
        if public_key is None:
            return None
        await _cache_public_key(public_key)
        try:
            return jwt.decode(
                token, public_key, algorithms=[settings.JWT_ALGORITHM]
            )
        except JWTError as e:
            logger.error("Failed to decode token: %s", e)
            return None
