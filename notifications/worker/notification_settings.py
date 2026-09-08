"""Получение настроек уведомлений пользователя через auth service
(GET /internal/users/{user_id}/notification-settings) с Redis-кэшем.

Слои:
  1. Redis-кэш (TTL 15min, защита от cache stampede через Redis SET NX)
  2. HTTP к auth-service (при промахе)
  3. Retry на недоступность auth (Kafka NACK + backoff)

Auth-сервис — единственный источник правды для настроек и дефолтных значений.
"""

import asyncio
import json
import logging
from functools import lru_cache
from uuid import UUID

import redis.asyncio as aioredis
from core.settings import settings
from http_client import HTTPClient

logger = logging.getLogger(__name__)

_STAMPED_WAIT_INTERVAL = 0.1
_STAMPED_WAIT_MAX = 5
_STAMPED_LOCK_TTL = 30


class NotificationSettingsResponse:
    """Результат получения настроек уведомлений."""

    __slots__ = ("notifications_enabled", "email_enabled", "sms_enabled", "push_enabled")

    def __init__(
        self,
        notifications_enabled: bool,
        email_enabled: bool,
        sms_enabled: bool,
        push_enabled: bool,
    ):
        self.notifications_enabled = notifications_enabled
        self.email_enabled = email_enabled
        self.sms_enabled = sms_enabled
        self.push_enabled = push_enabled

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationSettingsResponse":
        return cls(
            notifications_enabled=data["notifications_enabled"],
            email_enabled=data["email_enabled"],
            sms_enabled=data["sms_enabled"],
            push_enabled=data["push_enabled"],
        )

    def to_dict(self) -> dict:
        return {
            "notifications_enabled": self.notifications_enabled,
            "email_enabled": self.email_enabled,
            "sms_enabled": self.sms_enabled,
            "push_enabled": self.push_enabled,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@lru_cache(maxsize=1)
def _get_redis_pool() -> aioredis.ConnectionPool:
    """Создать пул соединений для кэширования настроек уведомлений."""
    return aioredis.ConnectionPool.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
        max_connections=50,
        decode_responses=True,
    )


def _get_auth_url(user_id: UUID) -> str:
    """Собрать URL для запроса к auth-service."""
    return f"{settings.AUTH_API_URL}/internal/users/{user_id}/notification-settings"


class AuthUnavailableError(Exception):
    """Auth-service недоступен — нужно ретраить."""


async def _fetch_from_auth(user_id: UUID) -> NotificationSettingsResponse | None:
    """Прямой HTTP-запрос к auth-service.

    Если auth недоступен (5xx, timeout, network) — бросает AuthUnavailableError
    для ретрая через Kafka NACK.
    Если пользователь не найден (404) — возвращаем None.
    """
    assert HTTPClient.client is not None
    try:
        response = await HTTPClient.client.get(
            _get_auth_url(user_id),
            headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
            timeout=5,
        )
    except Exception as exc:
        logger.warning(
            "auth-service unavailable for %s: %s — will retry", user_id, exc
        )
        raise AuthUnavailableError(
            f"auth-service unavailable for {user_id}: {exc}"
        ) from exc

    if response.status_code == 200:
        return NotificationSettingsResponse.from_dict(response.json())

    if response.status_code == 404:
        return None

    logger.error(
        "auth-service error for %s: %s — will retry", user_id, response.status_code
    )
    raise AuthUnavailableError(
        f"auth-service error for {user_id}: {response.status_code}"
    )


async def get_notification_settings(user_id: UUID) -> NotificationSettingsResponse | None:
    """Получить настройки пользователя с Redis-кэшем.

    Слои:
      1. Redis-кэш (TTL 15min)
      2. HTTP к auth-service (при промахе)
      3. Graceful degradation (если Redis упал -> HTTP; если auth упал -> дефолты)
      4. Dogpiling protection (Redis SET NX с TTL)

    Returns None, если пользователь не найден в auth-service (404).
    """
    cache_key = f"ntf:settings:{user_id}"
    lock_key = f"ntf:lock:{user_id}"

    # --- 1. Быстрое чтение из Redis ---
    redis_conn = None
    redis_read_failed = False
    try:
        redis_conn = aioredis.Redis.from_pool(_get_redis_pool())
        cached = await redis_conn.get(cache_key)
        if cached:
            return NotificationSettingsResponse.from_dict(json.loads(cached))
    except aioredis.RedisError as exc:
        logger.warning("Redis unavailable for read (%s): %s", cache_key, exc)
        redis_read_failed = True

    # --- 2. Dogpiling protection ---
    settings_data = None

    if redis_read_failed:
        # Fallback на asyncio.Lock, если Redis вообще недоступен
        lock = asyncio.Lock()
        async with lock:
            if redis_conn is not None:
                try:
                    cached = await redis_conn.get(cache_key)
                    if cached:
                        return NotificationSettingsResponse.from_dict(json.loads(cached))
                except aioredis.RedisError:
                    pass
            settings_data = await _fetch_from_auth(user_id)
            if settings_data is None:
                return None
            return settings_data

    # Redis-соединение доступно — используем для dogpiling protection
    if redis_conn is None:
        settings_data = await _fetch_from_auth(user_id)
        if settings_data is None:
            return None
        return settings_data

    # Пытаемся захватить Redis lock — SET NX с TTL
    lock_acquired = False
    try:
        lock_acquired = await redis_conn.set(lock_key, "1", ex=_STAMPED_LOCK_TTL, nx=True)
    except aioredis.RedisError as exc:
        logger.warning("Redis unavailable for lock (%s): %s — falling back to asyncio.Lock", lock_key, exc)

    if lock_acquired:
        try:
            # double-check после захвата лога
            cached = await redis_conn.get(cache_key)
            if cached:
                return NotificationSettingsResponse.from_dict(json.loads(cached))

            settings_data = await _fetch_from_auth(user_id)
            if settings_data is None:
                return None

            await redis_conn.set(cache_key, settings_data.to_json(), ex=settings.NOTIFICATION_SETTINGS_CACHE_TTL)
            return settings_data
        except Exception:
            raise
        finally:
            # Снимаем lock
            try:
                await redis_conn.delete(lock_key)
            except aioredis.RedisError:
                pass
    else:
        # Lock уже захвачен другим — ждём и пробуем прочитать кэш
        waited = 0.0
        while waited < _STAMPED_WAIT_MAX:
            await asyncio.sleep(_STAMPED_WAIT_INTERVAL)
            waited += _STAMPED_WAIT_INTERVAL

            try:
                cached = await redis_conn.get(cache_key)
                if cached:
                    return NotificationSettingsResponse.from_dict(json.loads(cached))
            except aioredis.RedisError:
                pass

        # Таймаут — fetch from auth в любом случае
        settings_data = await _fetch_from_auth(user_id)
        if settings_data is None:
            return None

        try:
            await redis_conn.set(cache_key, settings_data.to_json(), ex=settings.NOTIFICATION_SETTINGS_CACHE_TTL)
        except aioredis.RedisError as exc:
            logger.warning("Redis unavailable for write (%s): %s", cache_key, exc)

    return settings_data
