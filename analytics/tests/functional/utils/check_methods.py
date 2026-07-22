from http import HTTPStatus
from typing import Any

from aiohttp import ClientResponse


async def assert_status_return_json(
    response: ClientResponse, status: int
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Проверяет статус ответа и возвращает тело как JSON (может быть None для 204/202)."""
    assert response.status == status
    if response.status in (HTTPStatus.NO_CONTENT, HTTPStatus.ACCEPTED):
        return None
    return await response.json()


async def assert_status(response: ClientResponse, status: int) -> None:
    """Проверяет статус ответа без тела."""
    assert response.status == status
