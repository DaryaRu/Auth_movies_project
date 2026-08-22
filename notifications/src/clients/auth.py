"""Поиск уникальных таймзон аудитории через auth-service."""

from typing import Any
from uuid import uuid4

import httpx

from src.core.config import settings


async def search_distinct_timezones(
    audience_filter: dict[str, Any],
) -> list[str]:
    """Уникальные IANA-таймзоны активных пользователей, подходящих под audience_filter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.AUTH_API_URL}/internal/users/search/timezones/",
            json=audience_filter,
            headers={"X-Request-Id": str(uuid4())},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
