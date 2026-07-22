from datetime import datetime, timedelta, timezone
from uuid import uuid4

import aiohttp
import jwt
import pytest
import pytest_asyncio

from analytics.tests.settings import test_settings


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
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        yield session


@pytest.fixture(scope="session")
def generate_test_token():
    """Генерирует валидный JWT токен для тестов, подписанный приватным ключом."""
    with open(test_settings.private_key_path, "r", encoding="utf-8") as f:
        private_key = f.read()

    payload = {
        "sub": str(uuid4()), 
        "roles": ["user"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token
