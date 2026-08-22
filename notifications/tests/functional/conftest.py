"""Фикстуры функциональных тестов notifications-service."""

from typing import AsyncGenerator
from uuid import uuid4

import aiohttp
import pytest_asyncio
from settings import test_settings


@pytest_asyncio.fixture(scope="function")
async def http_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """HTTP-клиент для тестов."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        yield session
