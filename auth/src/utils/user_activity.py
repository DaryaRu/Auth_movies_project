"""Получение активности пользователя (закладки, оценки, рецензии) из user_actions-service."""

import logging
from typing import Any
from uuid import UUID, uuid4

import httpx

from src.core.config import settings
from src.databases import http_client

logger = logging.getLogger(__name__)

USER_ACTIVITY_URL = "/internal/users/{user_id}/activity/"

_EMPTY_ACTIVITY: dict[str, list[Any]] = {
    "bookmarks": [],
    "likes": [],
    "reviews": [],
}


async def get_user_activity(user_id: UUID) -> dict[str, list[Any]]:
    """Возвращает закладки/оценки/рецензии пользователя из user_actions-service.

    При недоступности user_actions-service (или другой ошибке) отдает пустые списки,
    а не поднимает исключение.
    """
    try:
        assert http_client.client is not None
        response = await http_client.client.get(
            f"{settings.USER_ACTIONS_API_URL}{USER_ACTIVITY_URL.format(user_id=user_id)}",
            headers={
                "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
                "X-Request-Id": str(uuid4()),
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Failed to fetch user activity for user %s: %s", user_id, exc
        )
        return dict(_EMPTY_ACTIVITY)
