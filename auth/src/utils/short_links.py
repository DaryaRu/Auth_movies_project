"""Работа с короткими ссылками через short-links-service."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


async def _get_redirect_url() -> str:
    """Получить redirect_url из настроек short-links-service.

    Значение настраивается в панели админа.
    По умолчанию — главная страница онлайн-кинотеатра.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SHORT_LINKS_API_URL}/settings/redirect-url/",
                timeout=5,
            )
            response.raise_for_status()
            return response.json()["redirect_url"]
    except httpx.HTTPError:
        logger.warning(
            "Не удалось получить redirect_url из short-links-service, "
            "использую значение по умолчанию"
        )
        return "http://localhost/"


async def create_short_link(
    user_id: UUID,
) -> str:
    """Создать короткую ссылку для подтверждения email.

    Args:
        user_id: Идентификатор пользователя.

    Returns:
        str: Короткая ссылка.

    Raises:
        httpx.HTTPError: Если запрос к short-links-service не удался.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    redirect_url = await _get_redirect_url()

    payload = {
        "user_id": str(user_id),
        "expires_at": expires_at.isoformat(),
        "redirect_url": redirect_url,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SHORT_LINKS_API_URL}/short-links/",
                json=payload,
                headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data["short_link"]
    except httpx.HTTPError as e:
        logger.error("Failed to create short link for user %s: %s", user_id, e)
        raise
    