"""Фабрика приложения."""

from logging import config as logging_config

from fastapi import FastAPI

from src.core import logger
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.routers import register_routers


def create_app() -> FastAPI:
    """Создаёт и настраивает приложение FastAPI."""
    logging_config.dictConfig(logger.LOGGING)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="WebSocket-шлюз для push-уведомлений",
        version="0.1.0",
        lifespan=lifespan,
    )

    register_routers(app)

    return app