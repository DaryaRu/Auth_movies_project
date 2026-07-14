from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.cache import close_cache, init_cache
from src.core.kafka import close_kafka, init_kafka


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    await init_kafka()
    yield
    await close_kafka()
    await close_cache()
