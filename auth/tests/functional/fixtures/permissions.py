"""Фикстуры прав доступа: создание и удаление через API."""

import uuid
from typing import Any, AsyncGenerator

import pytest_asyncio
from aiohttp import ClientSession
from functional.settings import test_settings

PERMISSIONS_URL = f"{test_settings.api_prefix}/permissions"


@pytest_asyncio.fixture(scope="function")
async def created_permission(
    session_http_client: ClientSession,
    superuser_headers: dict[str, str],
) -> AsyncGenerator[dict[str, Any], None]:
    """Создаёт право через API и удаляет его после теста."""
    payload = {
        "code": f"test:{uuid.uuid4().hex[:8]}",
        "name": f"Test permission {uuid.uuid4().hex[:8]}",
        "category": "test",
    }
    response = await session_http_client.post(
        f"{PERMISSIONS_URL}/", json=payload, headers=superuser_headers
    )
    permission = await response.json()
    yield permission
    await session_http_client.delete(
        f"{PERMISSIONS_URL}/{permission['id']}/", headers=superuser_headers
    )
