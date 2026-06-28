import logging
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from redis.asyncio import Redis

from core import config
from core.cache import key_builder
from db import elastic, redis
from db.redis import FaultTolerantRedisBackend


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
    FastAPICache.init(
        FaultTolerantRedisBackend(redis.redis),
        prefix="fastapi-cache",
        key_builder=key_builder,
    )
    logging.info("FastAPI cache initialized")
    elastic.es = AsyncElasticsearch(
        hosts=[f"http://{config.ELASTIC_HOST}:{config.ELASTIC_PORT}"]
    )
    yield
    await redis.redis.close()
    await elastic.es.close()
