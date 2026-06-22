"""Фикстуры для создания и удаления ролей через API и в БД."""

import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator

import pytest_asyncio
from aiohttp import ClientSession
from functional.settings import test_settings

ROLES_URL = f"{test_settings.api_prefix}/roles"


@pytest_asyncio.fixture(scope="function")
async def created_role(
    session_http_client: ClientSession,
    superuser_headers: dict[str, str],
) -> AsyncGenerator[dict[str, Any], None]:
    """Создаёт роль через API и удаляет её после теста."""
    payload = {
        "name": f"test_role_{uuid.uuid4().hex[:8]}",
        "description": "Test role",
    }
    response = await session_http_client.post(
        f"{ROLES_URL}/", json=payload, headers=superuser_headers
    )
    role = await response.json()
    yield role
    await session_http_client.delete(
        f"{ROLES_URL}/{role['id']}/", headers=superuser_headers
    )


@pytest_asyncio.fixture(scope="function")
async def system_role(
    pg_write_data: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Создаёт системную роль (is_system=True) напрямую в БД."""
    role_id = uuid.uuid4()
    now = datetime.now(UTC)
    data = {
        "id": role_id,
        "name": f"system_role_{uuid.uuid4().hex[:8]}",
        "description": "System role",
        "is_active": True,
        "is_system": True,
        "created_at": now,
        "updated_at": now,
    }
    await pg_write_data("roles", tuple(data.keys()), tuple(data.values()))
    yield {**data, "id": str(role_id)}
