"""Управление жизненным циклом приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.kafka import close_kafka, init_kafka
from src.db.postgres import PostgreSQL
from src.db.redis import Redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Управление жизненным циклом приложения."""
    await PostgreSQL.connect()
    await Redis.connect()
    await init_kafka()
    yield
    await close_kafka()
    await Redis.disconnect()
    await PostgreSQL.disconnect()
