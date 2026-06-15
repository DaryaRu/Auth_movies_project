from contextlib import asynccontextmanager

from fastapi import FastAPI
from logging import config as logging_config

from src.core import logger
from src.core.cache import close_cache, init_cache
from src.core.config import settings
from src.core.middlewares import register_middlewares
from src.core.routers import register_routers

logging_config.dictConfig(logger.LOGGING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управлять жизненным циклом приложения и подключениями к кешу."""
    await init_cache()
    yield
    await close_cache()


def create_app() -> FastAPI:
    """Создать и настроить экземпляр приложения FastAPI."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=("Сервис авторизации и аутентификации"),
        version="1.0.0",
        docs_url="/api/openapi",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    register_middlewares(app)
    register_routers(app)

    return app
