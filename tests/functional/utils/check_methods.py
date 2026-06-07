from typing import Any

from aiohttp import ClientResponse


async def assert_status_return_json(response: ClientResponse, status: int) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Checks responce status, return responce.json
    """
    assert response.status == status
    return await response.json()
