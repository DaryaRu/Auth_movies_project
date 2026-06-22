"""Fixtures for resilience tests."""

import os
import sys
from pathlib import Path

import httpx
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

# Должно быть определено до импорта src/core/config.py (через main.py),
# иначе TrustedHostMiddleware
# отклонит запросы с host: test
os.environ["ALLOW_HOSTS"] = "*"
# Добавляем src/ в sys.path, чтобы работали импорты из приложения
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


@pytest_asyncio.fixture(scope="session")
async def http_client():
    import db.elastic as db_elastic
    import db.redis as db_redis
    from db.redis import FaultTolerantRedisBackend
    from fastapi_cache import FastAPICache
    from main import app, key_builder

    db_redis.redis = Redis(host="127.0.0.1", port=6379)
    FastAPICache.init(
        FaultTolerantRedisBackend(db_redis.redis),
        prefix="fastapi-cache",
        key_builder=key_builder,
    )
    db_elastic.es = AsyncElasticsearch(hosts=["http://127.0.0.1:9200"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await db_elastic.es.close()
    await db_redis.redis.aclose()
