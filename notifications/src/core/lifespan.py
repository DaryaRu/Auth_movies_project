"""Управление жизненным циклом приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.kafka import close_kafka, init_kafka
from src.db.postgres import PostgreSQL


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Управление жизненным циклом приложения."""
    await PostgreSQL.connect()
    await init_kafka()
    yield
    await close_kafka()
    await PostgreSQL.disconnect()
