"""Фикстуры функциональных тестов notifications-service."""

from typing import AsyncGenerator, Awaitable, Callable
from uuid import uuid4

import aiohttp
import pytest_asyncio
from aiokafka import AIOKafkaConsumer
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
