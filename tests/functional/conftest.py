"""Инфраструктурные фикстуры: HTTP-клиент и подключение к БД."""

import asyncio
from typing import Any, Awaitable, Callable, Iterable

import aiohttp
import asyncpg
import pytest
import pytest_asyncio
from functional.settings import test_settings
from functional.utils.helpers import create_data, delete_data

pytest_plugins = ["functional.fixtures.users", "functional.fixtures.roles", "functional.fixtures.permissions"]

WriteData = Callable[
    [str, Iterable[str], Iterable[Any]],
    Awaitable[None],
]


@pytest.fixture(scope="session")
def event_loop():
    """Фикстуры и тест-функции используют один loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def http_client() -> aiohttp.ClientSession:
    """Function-scoped HTTP-клиент для тестов."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def session_http_client() -> aiohttp.ClientSession:
    """Session-scoped HTTP-клиент для async-фикстур, которым нужны API-вызовы."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def pg_client() -> asyncpg.Connection:
    """Подключение к PostgreSQL на время сессии."""
    dsn = (
        f"postgresql://{test_settings.postgres_user}:{test_settings.postgres_password}@"
        f"{test_settings.postgres_host}:{test_settings.postgres_port}/{test_settings.postgres_db}"
    )
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def pg_write_data(pg_client: asyncpg.Connection) -> WriteData:
    """Записывает данные в БД и удаляет все записи из таблиц после сессии."""
    used_tables: set[str] = set()

    async def inner(
        table: str, columns: Iterable[str], data: Iterable[Any]
    ) -> None:
        await create_data(pg_client, table, columns, data)
        used_tables.add(table)

    yield inner

    for table in used_tables:
        await delete_data(pg_client, table)
