"""Фикстуры функциональных тестов notifications-service."""

from datetime import datetime, timezone
from typing import AsyncGenerator, Awaitable, Callable
from uuid import uuid4

import aiohttp
import asyncpg
import pytest_asyncio
from aiokafka import AIOKafkaConsumer
from argon2 import PasswordHasher
from settings import test_settings


def _hash_password(password: str) -> str:
    """Хэширует пароль."""
    hasher = PasswordHasher(
        time_cost=test_settings.hash_time_cost,
        memory_cost=test_settings.hash_memory_cost,
        parallelism=test_settings.hash_parallelism,
    )
    return hasher.hash(password)


@pytest_asyncio.fixture(scope="session")
async def pg_auth_client() -> AsyncGenerator[asyncpg.Connection, None]:
    """Подключение к auth-db на время сессии."""
    dsn = (
        f"postgresql://{test_settings.auth_postgres_user}:{test_settings.auth_postgres_password}@"
        f"{test_settings.auth_postgres_host}:{test_settings.auth_postgres_port}/{test_settings.auth_postgres_db}"
    )
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def superuser_token(pg_auth_client: asyncpg.Connection) -> str:
    """JWT суперпользователя для StaffUserDep-эндпоинтов notifications-service.

    Заводится суперпользователь записью в auth-db, а токен получается обычным логином.
    """
    email = f"notifications-functest-superuser-{uuid4().hex[:8]}@example.com"
    password = "SuperUser123"
    now = datetime.now(timezone.utc)
    await pg_auth_client.execute(
        """
        INSERT INTO users
            (id, email, hashed_password, is_superuser, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, TRUE, TRUE, $4, $4)
        """,
        uuid4(),
        email,
        _hash_password(password),
        now,
    )

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        response = await session.post(
            f"{test_settings.auth_api_url}/login/",
            json={"email": email, "password": password},
        )
        data = await response.json()
        return data["access_token"]


@pytest_asyncio.fixture(scope="session")
async def regular_user_token() -> str:
    """JWT обычного пользователя.
    403 на StaffUserDep-эндпоинтах."""
    email = f"notifications-functest-user-{uuid4().hex[:8]}@example.com"
    password = "User123"

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        await session.post(
            f"{test_settings.auth_api_url}/registration/",
            json={"email": email, "password": password},
        )
        response = await session.post(
            f"{test_settings.auth_api_url}/login/",
            json={"email": email, "password": password},
        )
        data = await response.json()
        return data["access_token"]


@pytest_asyncio.fixture(scope="function")
async def http_client(
    superuser_token: str,
) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """HTTP-клиент для тестов."""
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={
            "X-Request-Id": str(uuid4()),
            "X-Internal-Secret": test_settings.internal_service_secret,
            "Authorization": f"Bearer {superuser_token}",
        },
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def auth_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """HTTP-клиент для регистрации тестовых пользователей напрямую в auth-service."""
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def kafka_consumer_factory() -> AsyncGenerator[
    Callable[[str], Awaitable[AIOKafkaConsumer]], None
]:
    """Фабрика Kafka-консьюмеров для тестов — свой consumer group на каждый
    вызов."""
    consumers: list[AIOKafkaConsumer] = []

    async def _make(topic: str) -> AIOKafkaConsumer:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=test_settings.kafka_brokers,
            group_id=f"functest-{uuid4().hex}",
            auto_offset_reset="earliest",
        )
        await consumer.start()
        consumers.append(consumer)
        return consumer

    yield _make

    for consumer in consumers:
        await consumer.stop()
