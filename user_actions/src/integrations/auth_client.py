"""Клиент для вызовов auth-сервиса."""

import logging
from uuid import uuid4

from src.core.config import settings
from src.db.http_client import HTTPClient

logger = logging.getLogger(__name__)


class AuthClient:
    """HTTP-клиент для межсервисного взаимодействия с auth-сервисом."""

    @classmethod
    async def verify_session(cls, sid: str) -> bool:
        """Проверить действительность сессии в auth-сервисе.

        Вызывает GET /internal/sessions/{sid}/ auth-сервиса (согласованный
        механизм отзыва доступа): сессия должна быть активна, а пользователь —
        существовать и быть активным.

        Returns:
            True, если сессия активна и пользователь существует;
            False, если сессия отозвана (logout, смена телефона, удаление
            аккаунта) или пользователь удалён/деактивирован.

        Raises:
            RuntimeError: при сетевых сбоях или непредвиденном ответе
                auth-сервиса — решается на стороне вызывающего (fail-closed).
        """
        client = HTTPClient.client
        if client is None:
            await HTTPClient.connect()
            client = HTTPClient.client

        assert client is not None, "HTTPClient must be connected"

        url = f"{settings.AUTH_API_URL}/internal/sessions/{sid}/"
        headers = {
            "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
            "X-Request-Id": str(uuid4()),
        }

        response = await client.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return True
        if response.status_code in (401, 403, 404):
            return False
        raise RuntimeError(
            f"auth-service session verify failed: status {response.status_code}"
        )

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
