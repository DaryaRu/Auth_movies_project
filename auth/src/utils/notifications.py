"""Отправка персональных уведомлений через notifications-service."""

import logging
from typing import Any
from uuid import UUID

import httpx

from src.core.config import settings
from src.databases import http_client
from src.databases import redis as redis_module
from src.exceptions import ProviderException
from src.utils.backoff import async_backoff

logger = logging.getLogger(__name__)

_TEMPLATE_ID_REDIS_KEY_PREFIX = "auth:notification_template_id:"


async def _fetch_template_id(code: str) -> str | None:
    """Получить template_id из notifications-service по code."""
    try:
        assert http_client.client is not None
        response = await http_client.client.get(
            f"{settings.NOTIFICATIONS_API_URL}/templates/by-code/{code}/",
            headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
            timeout=5,
        )
        if response.status_code != 200:
            logger.warning(
                "Failed to resolve template_id for code=%s: status %s",
                code,
                response.status_code,
            )
            return None
        return response.json().get("template_id")
    except Exception as e:
        logger.warning(
            "Failed to resolve template_id for code=%s: %s", code, e
        )
        return None


async def _get_template_id(code: str) -> str | None:
    """Получить template_id из кэша или notifications-service."""
    redis_key = f"{_TEMPLATE_ID_REDIS_KEY_PREFIX}{code}"
    client = redis_module.redis
    if client is not None:
        try:
            cached = await client.get(redis_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        except Exception as e:
            logger.warning(
                "Redis unavailable, fetching template_id directly: %s", e
            )

    template_id = await _fetch_template_id(code)
    if template_id and client is not None:
        try:
            await client.set(
                redis_key,
                template_id,
                ex=settings.NOTIFICATIONS_TEMPLATE_ID_CACHE_TTL,
            )
        except Exception as e:
            logger.warning(
                "Failed to cache template_id for code=%s: %s", code, e
            )
    return template_id


@async_backoff(exceptions=(httpx.HTTPError,))
async def _fetch_required_template_id(code: str) -> str | None:
    assert http_client.client is not None
    response = await http_client.client.get(
        f"{settings.NOTIFICATIONS_API_URL}/templates/by-code/{code}/",
        headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
        timeout=5,
    )
    response.raise_for_status()
    return response.json().get("template_id")


@async_backoff(exceptions=(httpx.HTTPError,))
async def _send_notification_request(
    user_id: UUID, template_id: str, payload: dict[str, Any]
) -> None:
    assert http_client.client is not None
    response = await http_client.client.post(
        f"{settings.NOTIFICATIONS_API_URL}/",
        json={
            "user_id": str(user_id),
            "template_id": template_id,
            "payload": payload,
        },
        headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
        timeout=5,
    )
    response.raise_for_status()


async def _notify_user_required(
    user_id: UUID, code: str, payload: dict[str, Any]
) -> None:
    """Резолвит template_id по коду и отправляет уведомление. Оба запроса с ретраями на сетевых ошибках.
    Если template_id не резолвился либо отправка не удалась после ретраев, то поднимает
    ProviderException."""
    try:
        template_id = await _fetch_required_template_id(code)
        if template_id is None:
            raise ProviderException()
        await _send_notification_request(user_id, template_id, payload)
    except httpx.HTTPError as exc:
        logger.error(
            "Required notification failed for code=%s user=%s: %s",
            code,
            user_id,
            exc,
        )
        raise ProviderException() from exc


async def notify_user(
    user_id: UUID,
    code: str,
    payload: dict[str, Any] | None = None,
    *,
    required: bool = False,
) -> None:
    """Отправляет персональное уведомление через notifications-service.

    required=False (по умолчанию): резолвит template_id через Redis-кэш, затем POST / с
    payload. Любая ошибка только логируется, не бросает исключение и не блокирует вызывающий код.

    required=True: те же запросы, но с ретраями и ProviderException.
    Использовать, когда без доставки операцию нельзя завершить.
    """
    if required:
        await _notify_user_required(user_id, code, payload or {})
        return

    template_id = await _get_template_id(code)
    if template_id is None:
        logger.warning("Skip notification: no template for code=%s", code)
        return

    try:
        assert http_client.client is not None
        response = await http_client.client.post(
            f"{settings.NOTIFICATIONS_API_URL}/",
            json={
                "user_id": str(user_id),
                "template_id": template_id,
                "payload": payload or {},
            },
            headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
            timeout=5,
        )
        if response.status_code != 202:
            logger.warning(
                "Failed to send notification code=%s to user=%s: status %s",
                code,
                user_id,
                response.status_code,
            )
    except Exception as e:
        logger.warning(
            "Failed to send notification code=%s to user=%s: %s",
            code,
            user_id,
            e,
        )


# Ключ кэша воркера: ntf:settings:{user_id}
_NOTIFICATION_SETTINGS_REDIS_KEY_PREFIX = "ntf:settings:"


async def invalidate_notification_settings_cache(user_id: UUID) -> None:
    """Удалить кэш настроек уведомлений пользователя из Redis.

    Вызывается из auth-сервиса после PATCH настроек, чтобы воркер
    перезапросил свежие данные из auth-service при следующей обработке.
    """
    redis_conn = redis_module.redis
    if redis_conn is None:
        logger.warning(
            "Redis unavailable, skipping notification cache invalidation"
        )
        return

    redis_key = f"{_NOTIFICATION_SETTINGS_REDIS_KEY_PREFIX}{user_id}"
    try:
        await redis_conn.delete(redis_key)
        logger.debug(
            "Notification settings cache invalidated for user=%s", user_id
        )
    except Exception as e:
        logger.warning(
            "Failed to invalidate notification settings cache for user=%s: %s",
            user_id,
            e,
        )
