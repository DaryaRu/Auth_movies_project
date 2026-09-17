from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Collection,
    Iterable,
)
from uuid import uuid4

import aiohttp
import asyncpg
import pytest_asyncio

from tests.functional.utils.auth_api import register_and_login
from tests.functional.utils.helpers import (
    create_data,
    delete_data,
)
from tests.settings import test_settings

WriteData = Callable[
    [str, Collection[str], Iterable[Any]],
    Awaitable[None],
]


@pytest_asyncio.fixture(scope="function")
async def http_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Function-scoped HTTP-клиент для тестов.
    DummyCookieJar нужен, чтобы куки не отправлялись и не переходили между тестами, для изоляция.
    """
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def pg_client() -> AsyncGenerator[asyncpg.Connection, None]:
    """Session-scoped PostgreSQL connection."""
    dsn = (
        f"postgresql://{test_settings.postgres_user}:{test_settings.postgres_password}@"
        f"{test_settings.postgres_host}:{test_settings.postgres_port}/{test_settings.postgres_db}"
    )
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def pg_write_data(pg_client: asyncpg.Connection) -> AsyncGenerator[WriteData, None]:
    """Write data to DB and clean up after session."""
    used_tables: set[str] = set()

    async def inner(
        table: str, columns: Collection[str], data: Iterable[Any]
    ) -> None:
        await create_data(pg_client, table, columns, data)
        used_tables.add(table)

    yield inner

    for table in used_tables:
        await delete_data(pg_client, table)


@pytest_asyncio.fixture(scope="session")
async def generate_test_token() -> str:
    """Access-токен реального пользователя с активной сессией.

    Регистрирует и логинит одного пользователя в auth-service на всю сессию.
    user_actions теперь проверяет сессию через auth-service, поэтому тестам
    нужен реальный токен с валидным sid, а не самоподписанный фейковый.
    """
    session = await register_and_login()
    return session.access_token


@pytest_asyncio.fixture(scope="function")
async def test_auth_session():
    """AuthSession реального пользователя (user_id + access + refresh токены).

    Function-scoped: каждый тест получает своего нового пользователя,
    потому что тесты отзыва (logout, удаление аккаунта) уничтожают
    сессию/аккаунт и ломают её для следующих тестов.
    """
    return await register_and_login()
