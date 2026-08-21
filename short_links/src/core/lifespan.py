"""Управление жизненным циклом приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.postgres import PostgreSQL


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Управление жизненным циклом приложения."""
    await PostgreSQL.connect()
    yield
    await PostgreSQL.disconnect()