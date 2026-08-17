"""Получение email пользователя через auth service (GET /internal/users/{user_id}/)."""

from uuid import UUID, uuid4

import httpx
from core.settings import settings


async def get_email(user_id: UUID) -> str | None:
    """Получить email пользователя (или None, если пользователь не найден или email не указан).
    Сетевые ошибки/5xx от auth service пробрасываются и обрабатываются как retry уже на уровне консьюмера."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.AUTH_API_URL}/internal/users/{user_id}/",
            headers={"X-Request-Id": str(uuid4())},
            timeout=5,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("email")
