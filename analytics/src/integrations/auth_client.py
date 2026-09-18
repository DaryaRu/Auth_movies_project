"""Клиент для вызовов auth-сервиса."""

import logging
from uuid import uuid4

from src.core.config import settings
from src.db import http_client

logger = logging.getLogger(__name__)


class AuthClient:
    """HTTP-клиент для межсервисного взаимодействия с auth-сервисом."""

    @classmethod
    async def verify_session(cls, sid: str) -> bool:
        """Проверить действительность сессии в auth-сервисе.

        Вызывает GET /internal/sessions/{sid}/ auth-сервиса (согласованный
        механизм отзыва доступа): сессия должна быть активна, а
        пользователь — существовать и быть активным.

        Returns:
            True, если сессия активна и пользователь существует;
            False, если сессия отозвана (logout, смена телефона, удаление
            аккаунта) или пользователь удалён/деактивирован.

        Raises:
            RuntimeError: при сетевых сбоях или непредвиденном ответе
                auth-сервиса — решается на стороне вызывающего (fail-closed).
        """
        assert http_client.client is not None, "HTTPClient must be connected"

        url = f"{settings.AUTH_API_URL}/internal/sessions/{sid}/"
        headers = {
            "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
            "X-Request-Id": str(uuid4()),
        }

        response = await http_client.client.get(
            url, headers=headers, timeout=5
        )
        if response.status_code == 200:
            return True
        if response.status_code in (401, 403, 404):
            return False
        raise RuntimeError(
            f"auth-service session verify failed: status {response.status_code}"
        )
