"""Фикстуры пользователей для тестов смены email."""

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable

import aiohttp
import pytest
import pytest_asyncio
from functional.settings import test_settings
from functional.utils.helpers import hash_password

WriteData = Callable[
    [str, Iterable[str], Iterable[Any]],
    Awaitable[None],
]


@pytest.fixture(scope="session")
def email_change_user_data() -> dict[str, Any]:
    """Фикстура под тесты смены email.
    Успешный /verify-new-email/ доходит до настоящего обновления email.
    """
    return {
        "id": uuid.uuid4(),
        "email": "email_change_user@example.com",
        "password": "testpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture(scope="session")
async def create_email_change_user(
    pg_write_data: WriteData, email_change_user_data: dict[str, Any]
) -> None:
    """Создает пользователя в БД перед тестами смены email."""
    data = {
        "id": email_change_user_data["id"],
        "email": email_change_user_data["email"],
        "hashed_password": hash_password(email_change_user_data["password"]),
        "is_superuser": email_change_user_data["is_superuser"],
        "is_active": email_change_user_data["is_active"],
        "created_at": email_change_user_data["created_at"],
        "updated_at": email_change_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest_asyncio.fixture(scope="session")
async def email_change_user_token(
    session_http_client: aiohttp.ClientSession,
    email_change_user_data: dict[str, Any],
    create_email_change_user: None,
) -> str:
    """Логинится как пользователь для тестов смены email и возвращает access_token."""
    response = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={
            "email": email_change_user_data["email"],
            "password": email_change_user_data["password"],
        },
    )
    data = await response.json()
    return data["access_token"]
