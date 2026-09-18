from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import aiohttp
import jwt
import pytest_asyncio
from redis.asyncio import Redis

from analytics.tests.settings import test_settings


@pytest_asyncio.fixture(scope="function")
async def http_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Function-scoped HTTP-клиент для тестов.
    DummyCookieJar нужен, чтобы куки не отправлялись и не переходили между тестами, для изоляция.
    """
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        # limit=0 снимает ограничения на число одновременных соединений.
        # Нужно для test_create_event_buffer_full, чтобы запросы уходили
        # одновременно, и гарантированно достигалось переполнение буфера.
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def generate_test_token() -> str:
    """Валидный access-токен для тестов, подписанный приватным ключом.

    get_current_user требует claim `type=access` и проверяет действительность
    сессии по `sid` (через кэш в Redis / auth-service). Токен самоподписанный,
    поэтому сразу кладём в Redis отметку о валидной сессии по тому же ключу,
    что использует analytics-service (`analytics:session_valid:{sid}`), без
    реальной регистрации/логина в auth-service.
    """
    with open(test_settings.private_key_path, "r", encoding="utf-8") as f:
        private_key = f.read()

    sid = str(uuid4())
    payload = {
        "sub": str(uuid4()),
        "sid": sid,
        "type": "access",
        "roles": ["user"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")

    redis_client = Redis(
        host=test_settings.redis_host, port=test_settings.redis_port, db=0
    )
    try:
        await redis_client.set(f"analytics:session_valid:{sid}", "1", ex=1800)
    finally:
        await redis_client.aclose()

    return token
