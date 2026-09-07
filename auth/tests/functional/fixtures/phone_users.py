"""Фикстуры пользователей с телефоном: 2FA-логин и смена номера."""

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
def phone_user_data() -> dict[str, Any]:
    """Данные пользователя с телефоном из TEST_PHONE_NUMBER (.env) для тестов 2FA и смены номера."""
    return {
        "id": uuid.uuid4(),
        "email": "phone_user@example.com",
        "phone": test_settings.test_phone_number,
        "password": "testpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture(scope="session")
async def create_phone_user(
    pg_write_data: WriteData, phone_user_data: dict[str, Any]
) -> None:
    """Создает пользователя с телефоном в БД перед запуском 2FA-тестов."""
    data = {
        "id": phone_user_data["id"],
        "email": phone_user_data["email"],
        "phone": phone_user_data["phone"],
        "hashed_password": hash_password(phone_user_data["password"]),
        "is_superuser": phone_user_data["is_superuser"],
        "is_active": phone_user_data["is_active"],
        "created_at": phone_user_data["created_at"],
        "updated_at": phone_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest.fixture(scope="session")
def phone_change_user_data() -> dict[str, Any]:
    """Фикстура специально изолирована под тесты смены номера.

    В отличие от active_user_data, эта строка реально изменяется:
    test_confirm_phone_change_success доходит до настоящего UPDATE
    (phone меняется с NULL на реальное значение).
    """
    return {
        "id": uuid.uuid4(),
        "email": "phone_change_user@example.com",
        "password": "testpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture(scope="session")
async def create_phone_change_user(
    pg_write_data: WriteData, phone_change_user_data: dict[str, Any]
) -> None:
    """Создает пользователя без телефона в БД перед тестами смены номера."""
    data = {
        "id": phone_change_user_data["id"],
        "email": phone_change_user_data["email"],
        "hashed_password": hash_password(phone_change_user_data["password"]),
        "is_superuser": phone_change_user_data["is_superuser"],
        "is_active": phone_change_user_data["is_active"],
        "created_at": phone_change_user_data["created_at"],
        "updated_at": phone_change_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest_asyncio.fixture(scope="session")
async def phone_change_user_token(
    session_http_client: aiohttp.ClientSession,
    phone_change_user_data: dict[str, Any],
    create_phone_change_user: None,
) -> str:
    """Логинится как пользователь без телефона и возвращает access_token."""
    response = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={
            "email": phone_change_user_data["email"],
            "password": phone_change_user_data["password"],
        },
    )
    data = await response.json()
    return data["access_token"]


@pytest.fixture(scope="session")
def phone_change_full_flow_user_data() -> dict[str, Any]:
    """Данные пользователя без телефона."""
    return {
        "id": uuid.uuid4(),
        "email": "phone_change_full_flow_user@example.com",
        "password": "testpassword123",
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture(scope="session")
async def create_phone_change_full_flow_user(
    pg_write_data: WriteData, phone_change_full_flow_user_data: dict[str, Any]
) -> None:
    """Создает пользователя без телефона в БД перед тестом полного флоу смены номера."""
    data = {
        "id": phone_change_full_flow_user_data["id"],
        "email": phone_change_full_flow_user_data["email"],
        "hashed_password": hash_password(
            phone_change_full_flow_user_data["password"]
        ),
        "is_superuser": phone_change_full_flow_user_data["is_superuser"],
        "is_active": phone_change_full_flow_user_data["is_active"],
        "created_at": phone_change_full_flow_user_data["created_at"],
        "updated_at": phone_change_full_flow_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))


@pytest_asyncio.fixture(scope="session")
async def phone_change_full_flow_user_token(
    session_http_client: aiohttp.ClientSession,
    phone_change_full_flow_user_data: dict[str, Any],
    create_phone_change_full_flow_user: None,
) -> str:
    """Логинится как пользователь без телефона и возвращает access_token."""
    response = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={
            "email": phone_change_full_flow_user_data["email"],
            "password": phone_change_full_flow_user_data["password"],
        },
    )
    data = await response.json()
    return data["access_token"]
