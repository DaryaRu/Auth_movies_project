"""Клиент для вызовов auth-сервиса."""

import logging
from uuid import uuid4

from src.core.config import settings
from src.db.http_client import HTTPClient

logger = logging.getLogger(__name__)


class AuthClient:
    """HTTP-клиент для межсервисного взаимодействия с auth-сервисом."""

    @classmethod
    async def get_users_names(
        cls, user_ids: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """Получить full_name и nickname для списка user_ids.

        Вызывает POST /api/v1/internal/users/names auth-сервиса.

        Args:
            user_ids: Список UUID пользователей в виде строк.

        Returns:
            Словарь {user_id_str: {"full_name": ...|None, "nickname": ...|None}}.
            При недоступности auth-сервиса или любом сбое возвращает пустой
            словарь, чтобы создание рецензии не падало (деградация до «Аноним»).
        """
        if not user_ids:
            return {}

        try:
            client = HTTPClient.client
            if client is None:
                await HTTPClient.connect()
                client = HTTPClient.client

            assert client is not None, "HTTPClient must be connected"

            url = f"{settings.AUTH_API_URL}/internal/users/names"

            headers = {
                "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
                "X-Request-Id": str(uuid4()),
            }

            response = await client.post(
                url, json={"user_ids": user_ids}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            logger.exception(
                "Failed to fetch user names from auth service for %s users",
                len(user_ids),
            )
            return {}
