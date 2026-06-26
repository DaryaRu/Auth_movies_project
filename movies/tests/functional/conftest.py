"""Fixtures for functional tests."""

import uuid

import aiohttp
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

from functional.settings import test_settings
from functional.utils.helpers import create_index, delete_index, load_data

pytest_plugins = [
    'functional.fixtures.films',
    'functional.fixtures.genres',
    'functional.fixtures.persons',
]


@pytest_asyncio.fixture(scope="session")
async def es_client():
    """Session-scoped Elasticsearch async client."""
    host = (
        f"http://{test_settings.elastic_host}:{test_settings.elastic_port}"
    )
    client = AsyncElasticsearch(hosts=[host])
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session")
async def redis_client():
    """Session-scoped Redis async client."""
    client = Redis(
        host=test_settings.redis_host, port=test_settings.redis_port
    )
    yield client
    await client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def flush_cache(redis_client: Redis):
    """Flushe Redis cache before each test."""
    await redis_client.flushdb()


@pytest_asyncio.fixture(loop_scope="function")
async def http_client():
    """Function-scoped aiohttp client session."""
    headers = {
        "X-Request-Id": str(uuid.uuid4())
    }
    async with aiohttp.ClientSession(
        base_url=test_settings.api_url,
        headers=headers
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def es_write_data(es_client: AsyncElasticsearch):
    """Fixture for loading test data into Elasticsearch."""
    created_indices = []

    async def inner(index: str, schema: dict, data: list[dict]) -> None:
        await create_index(es_client, index, schema)
        await load_data(es_client, index, data)
        created_indices.append(index)

    yield inner

    for index in created_indices:
        await delete_index(es_client, index)
