"""Управление жизненным циклом приложения."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core import redis
from src.core.logger import TokenRedactionFilter
from src.core.pubsub_listener import start, stop
from src.ws_registry import _connections

logger = logging.getLogger(__name__)


def _apply_token_redaction() -> None:
    """Добавляет фильтр маскировки токенов ко всем существующим хендлерам."""
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, TokenRedactionFilter) for f in handler.filters):
            handler.addFilter(TokenRedactionFilter())
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        for handler in lg.handlers:
            if not any(isinstance(f, TokenRedactionFilter) for f in handler.filters):
                handler.addFilter(TokenRedactionFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Управление жизненным циклом приложения."""
    _apply_token_redaction()
    redis.init()
    await redis.redis.ping()
    logger.info("Connected to Redis")

    pubsub_task = start()

    yield

    for _user_id, conns in list(_connections.items()):
        for ws in list(conns):
            try:
                await ws.close(code=1001, reason="Server shutting down")
            except Exception:
                pass
    logger.info("All WebSocket connections closed")

    await stop(pubsub_task)

    await redis.close()
    logger.info("Redis connection closed")