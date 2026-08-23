from typing import AsyncGenerator
from uuid import uuid4

import aiohttp
import asyncpg
import pytest_asyncio

from tests.settings import test_settings


@pytest_asyncio.fixture(scope="function")
async def http_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Function-scoped HTTP-клиент для тестов."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={
            "X-Request-Id": str(uuid4()),
            "X-Internal-Secret": test_settings.internal_service_secret,
        },
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
