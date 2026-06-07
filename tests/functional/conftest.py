"""Fixtures for functional tests."""

import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, Iterable

import aiohttp
import asyncpg
import pytest
import pytest_asyncio
from functional.settings import test_settings
from functional.utils.helpers import create_data, delete_data, hash_password

WriteData = Callable[
    [str, Iterable[str], Iterable[Any]],
    Awaitable[None],
]


@pytest_asyncio.fixture(loop_scope="function")
async def http_client():
    """Function-scoped aiohttp client session."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def pg_client() -> AsyncGenerator[asyncpg.Connection, None]:
    """Session-scoped PostgreSQL async client."""
    dsn = f"postgresql://{test_settings.postgres_user}:{test_settings.postgres_password}@" \
          f"{test_settings.postgres_host}:{test_settings.postgres_port}/{test_settings.postgres_db}"
    
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@pytest.fixture(scope="session")
def active_user_data() -> Generator[dict[str, Any], None, None]:
    """Create an active regular user in database."""
    user_data = {
        "id": uuid.uuid4(),
        "email": "test_user@example.com",
        "password": "testpassword123",
        "is_staff": False,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    
    yield user_data


@pytest.fixture(scope="session")
def active_admin_data() -> Generator[dict[str, Any], None, None]:
    """Create an active admin user in database."""
    admin_data = {
        "id": uuid.uuid4(),
        "email": "admin@example.com",
        "password": "adminpassword123",
        "is_staff": True,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    
    yield admin_data


@pytest_asyncio.fixture(scope="session")
async def pg_write_data(pg_client: asyncpg.Connection) -> AsyncGenerator[WriteData, None]:
    used_tables = set()

    async def inner(table: str, columns: Iterable[str], data: Iterable[Any]) -> None:
        await create_data(pg_client, table, columns, data)
        used_tables.add(table)

    yield inner
    for table in used_tables:
        await delete_data(pg_client, table)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_admin(pg_write_data: WriteData, active_admin_data: dict[str, Any]):
    """Create an active admin user in database."""
    data = {
        "hashed_password": hash_password(active_admin_data["password"]),
        "id": active_admin_data["id"],
        "email": active_admin_data["email"],
        "is_staff": active_admin_data["is_staff"],
        "is_active": active_admin_data["is_active"],
        "created_at": active_admin_data["created_at"],
        "updated_at": active_admin_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))
    

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_user(pg_write_data: WriteData, active_user_data: dict[str, Any]):
    """Create an active admin user in database."""
    data = {
        "hashed_password": hash_password(active_user_data["password"]),
        "id": active_user_data["id"],
        "email": active_user_data["email"],
        "is_staff": active_user_data["is_staff"],
        "is_active": active_user_data["is_active"],
        "created_at": active_user_data["created_at"],
        "updated_at": active_user_data["updated_at"],
    }
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))
