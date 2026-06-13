"""Инфраструктурные фикстуры: HTTP-клиенты и подключение к БД."""

import asyncio
from typing import Any, AsyncGenerator, Awaitable, Callable, Iterable

import aiohttp
import asyncpg
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from functional.settings import test_settings
from functional.utils.helpers import create_data, delete_data

pytest_plugins = [
    "functional.fixtures.users",
    "functional.fixtures.roles",
    "functional.fixtures.permissions",
]

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
    """Function-scoped HTTP-клиент для тестов.
    DummyCookieJar нужен, чтобы куки не отправлялись и не переходили между тестами, для изоляция.
    """
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def cookie_http_client() -> aiohttp.ClientSession:
    """Клиент для тестов с cookie (login, refresh, logout).
    CookieJar(unsafe=True) сохраняет Set-Cookie и автоматически отправляет куки в следующих запросах.
    unsafe=True нужен для hostname без точки (fastapi-auth).
    После логина нужно прочитать ответ до конца (await response.json()), иначе aiohttp
    не завершит обработку Set-Cookie и куки не попадут в jar.
    """
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False),
        cookie_jar=aiohttp.CookieJar(unsafe=True),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def session_http_client() -> aiohttp.ClientSession:
    """Клиент только для session-scoped фикстур, которым нужны API-вызовы
    (например, superuser_token, regular_user_token).
    Один экземпляр на всю сессию, куки не сохраняются.
    """
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def pg_client() -> AsyncGenerator[asyncpg.Connection, None]:
    """Подключение к PostgreSQL на время сессии."""
    dsn = (
        f"postgresql://{test_settings.postgres_user}:{test_settings.postgres_password}@"
        f"{test_settings.postgres_host}:{test_settings.postgres_port}/{test_settings.postgres_db}"
    )
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def pg_write_data(pg_client: asyncpg.Connection) -> AsyncGenerator[WriteData, None]:
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
        
        
@pytest_asyncio.fixture(scope="session")
async def redis_client():
    """Session-scoped Redis async client."""
    client = Redis(
        host=test_settings.redis_host, port=test_settings.redis_port
    )
    yield client
    await client.aclose()


@pytest_asyncio.fixture()
async def flush_redis_db(redis_client: Redis) -> None:
    """Flushe Redis cache before each test."""
    await redis_client.flushdb()
