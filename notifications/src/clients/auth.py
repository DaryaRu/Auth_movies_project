"""Поиск уникальных таймзон аудитории через auth-service."""

from typing import Any
from uuid import uuid4

from src.core.config import settings
from src.db.http_client import HTTPClient


async def search_distinct_timezones(
    audience_filter: dict[str, Any],
) -> list[str]:
    """Уникальные IANA-таймзоны активных пользователей, подходящих под audience_filter."""
    assert HTTPClient.client is not None
    response = await HTTPClient.client.post(
        f"{settings.AUTH_API_URL}/internal/users/search/timezones/",
        json=audience_filter,
        headers={"X-Request-Id": str(uuid4())},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
