"""Поиск аудитории для рассылки через auth service (POST /internal/users/search/)."""

from typing import Any
from uuid import UUID, uuid4

import httpx
from core.settings import settings


async def search_users(audience_filter: dict[str, Any]) -> list[UUID]:
    """Получить список id активных пользователей, подходящих под audience_filter.
    Сетевые ошибки/5xx от auth service пробрасываются и обрабатываются как retry на уровне консьюмера."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.AUTH_API_URL}/internal/users/search/",
            json=audience_filter,
            headers={
                "X-Request-Id": str(uuid4()),
                "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
            },
            timeout=10,
        )
        response.raise_for_status()
        return [UUID(user_id) for user_id in response.json()]


async def search_bookmark_users(content_id: UUID) -> list[UUID]:
    """Резолв аудитории notification_triggers: список id пользователей,
    добавивших content_id в закладки (GET /internal/bookmarks/{content_id}/users/
    у user-actions-service)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.USER_ACTIONS_API_URL}/internal/bookmarks/{content_id}/users/",
            headers={
                "X-Request-Id": str(uuid4()),
                "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
            },
            timeout=10,
        )
        response.raise_for_status()
        return [UUID(user_id) for user_id in response.json()]
