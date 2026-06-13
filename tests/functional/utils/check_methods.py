from typing import Any

from aiohttp import ClientResponse


async def assert_status_return_json(
    response: ClientResponse, status: int
) -> dict[str, Any] | list[dict[str, Any]]:
    """Проверяет статус ответа и возвращает тело как JSON."""
    assert response.status == status
    return await response.json()


async def assert_status(response: ClientResponse, status: int) -> None:
    """Проверяет статус ответа без тела (например, 204 No Content)."""
    assert response.status == status
