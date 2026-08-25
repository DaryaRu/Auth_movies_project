from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.core.cache import close_cache, init_cache
from src.core.kafka import close_kafka, init_kafka
from src.db import http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    await init_kafka()
    http_client.client = httpx.AsyncClient()
    yield
    await http_client.client.aclose()
    await close_kafka()
    await close_cache()
