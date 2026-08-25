"""Управление жизненным циклом приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.http_client import HTTPClient
from src.db.postgres import PostgreSQL
from src.db.redis import Redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Управление жизненным циклом приложения."""
    await PostgreSQL.connect()
    Redis.connect()
    await HTTPClient.connect()
    yield
    await HTTPClient.disconnect()
    await PostgreSQL.disconnect()
    Redis.disconnect()
