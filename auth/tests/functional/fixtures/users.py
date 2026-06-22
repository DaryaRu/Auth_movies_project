"""Фикстуры пользователей: данные, создание в БД, токены и заголовки авторизации."""

import uuid
from datetime import UTC, datetime
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
def active_user_data() -> dict[str, Any]:
    """Данные обычного пользователя для тестов аутентификации."""
    return {
        "id": uuid.uuid4(),
        "email": "test_user@example.com",
        "phone": "+79000000000",
        "password": "testpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_user(pg_write_data: WriteData, active_user_data: dict[str, Any]) -> None:
    """Создаёт обычного пользователя в БД перед запуском тестов."""
    data = {
        "id": active_user_data["id"],
        "email": active_user_data["email"],
        "phone": active_user_data["phone"],
        "hashed_password": hash_password(active_user_data["password"]),
        "is_superuser": active_user_data["is_superuser"],
        "is_active": active_user_data["is_active"],
        "created_at": active_user_data["created_at"],
        "updated_at": active_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest.fixture(scope="session")
def superuser_data() -> dict[str, Any]:
    """Данные суперпользователя для тестов ролей."""
    return {
        "id": uuid.uuid4(),
        "email": "superuser_roles@example.com",
        "password": "superpassword123",
        "is_superuser": True,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest_asyncio.fixture(scope="session")
async def create_superuser(pg_write_data: WriteData, superuser_data: dict[str, Any]) -> None:
    """Создаёт суперпользователя в БД."""
    data = {
        "id": superuser_data["id"],
        "email": superuser_data["email"],
        "hashed_password": hash_password(superuser_data["password"]),
        "is_superuser": superuser_data["is_superuser"],
        "is_active": superuser_data["is_active"],
        "created_at": superuser_data["created_at"],
        "updated_at": superuser_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest_asyncio.fixture(scope="session")
async def superuser_token(
    session_http_client: aiohttp.ClientSession,
    superuser_data: dict[str, Any],
    create_superuser: None,
) -> str:
    """Логинится как суперпользователь и возвращает access_token."""
    response = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={"email": superuser_data["email"], "password": superuser_data["password"]},
    )
    data = await response.json()
    return data["access_token"]


@pytest.fixture(scope="session")
def regular_user_for_roles_data() -> dict[str, Any]:
    """Данные обычного пользователя для тестов назначения ролей."""
    return {
        "id": uuid.uuid4(),
        "email": "regular_roles@example.com",
        "password": "regularpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest_asyncio.fixture(scope="session")
async def create_regular_user_for_roles(
    pg_write_data: WriteData,
    regular_user_for_roles_data: dict[str, Any],
) -> None:
    """Создаёт обычного пользователя для тестов ролей в БД."""
    data = {
        "id": regular_user_for_roles_data["id"],
        "email": regular_user_for_roles_data["email"],
        "hashed_password": hash_password(regular_user_for_roles_data["password"]),
        "is_superuser": regular_user_for_roles_data["is_superuser"],
        "is_active": regular_user_for_roles_data["is_active"],
        "created_at": regular_user_for_roles_data["created_at"],
        "updated_at": regular_user_for_roles_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest.fixture
def no_auth_headers() -> dict[str, str]:
    """Пустые заголовки для проверки ответа 401."""
    return {}


@pytest.fixture
def superuser_headers(superuser_token: str) -> dict[str, str]:
    """Заголовок Authorization для суперпользователя."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest.fixture
def regular_user_headers(regular_user_token: str) -> dict[str, str]:
    """Заголовок Authorization для обычного пользователя."""
    return {"Authorization": f"Bearer {regular_user_token}"}


@pytest_asyncio.fixture(scope="session")
async def regular_user_token(
    session_http_client: aiohttp.ClientSession,
    regular_user_for_roles_data: dict[str, Any],
    create_regular_user_for_roles: None,
) -> str:
    """Логинится как обычный пользователь и возвращает access_token."""
    response = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={
            "email": regular_user_for_roles_data["email"],
            "password": regular_user_for_roles_data["password"],
        },
    )
    data = await response.json()
    return data["access_token"]
