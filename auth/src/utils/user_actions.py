"""Очистка данных пользователя в user_actions-service при удалении аккаунта."""

import logging
from uuid import UUID

import httpx

from src.core.config import settings
from src.databases import http_client
from src.utils.backoff import async_backoff

logger = logging.getLogger(__name__)

USER_ACTIONS_DELETE_URL = "/internal/users/{user_id}/actions/"


class UserActionsUnavailableError(Exception):
    """Данные не удалены, так как user_actions-service недоступен после всех попыток."""


@async_backoff(exceptions=(httpx.HTTPError,))
async def _request_delete(user_id: UUID) -> None:
    assert http_client.client is not None
    response = await http_client.client.delete(
        f"{settings.USER_ACTIONS_API_URL}{USER_ACTIONS_DELETE_URL.format(user_id=user_id)}",
        headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
        timeout=10,
    )
    response.raise_for_status()


async def delete_user_data(user_id: UUID) -> None:
    """Удаляет закладки, оценки, рецензии пользователя в user_actions-service."""
    try:
        await _request_delete(user_id)
    except httpx.HTTPError as exc:
        logger.error(
            "Failed to delete user_actions data for user %s: %s", user_id, exc
        )
        raise UserActionsUnavailableError(
            f"user_actions-service недоступен: {exc}"
        ) from exc
