"""Отправка персональных уведомлений через notifications-service."""

import logging
from typing import Any
from uuid import UUID

from src.core.config import settings
from src.db.http_client import HTTPClient
from src.db.redis import Redis

logger = logging.getLogger(__name__)

_TEMPLATE_ID_REDIS_KEY_PREFIX = "user_actions:notification_template_id:"


async def _fetch_template_id(code: str) -> str | None:
    """Получить template_id из notifications-service по code."""
    try:
        assert HTTPClient.client is not None
        response = await HTTPClient.client.get(
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
    redis_client = Redis.get_client()
    if redis_client is not None:
        try:
            cached = await redis_client.get(redis_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        except Exception as e:
            logger.warning(
                "Redis unavailable, fetching template_id directly: %s", e
            )

    template_id = await _fetch_template_id(code)
    if template_id and redis_client is not None:
        try:
            await redis_client.set(
                redis_key,
                template_id,
                ex=settings.NOTIFICATIONS_TEMPLATE_ID_CACHE_TTL,
            )
        except Exception as e:
            logger.warning(
                "Failed to cache template_id for code=%s: %s", code, e
            )
    return template_id


async def notify_user(
    user_id: UUID, code: str, payload: dict[str, Any] | None = None
) -> None:
    """Отправить персональное уведомление."""
    template_id = await _get_template_id(code)
    if template_id is None:
        logger.warning("Skip notification: no template for code=%s", code)
        return

    try:
        assert HTTPClient.client is not None
        response = await HTTPClient.client.post(
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
