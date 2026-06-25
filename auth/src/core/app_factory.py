from contextlib import asynccontextmanager
from logging import config as logging_config

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from src.core import logger
from src.core.cache import close_cache, init_cache
from src.core.config import settings
from src.core.middlewares import register_middlewares
from src.core.routers import register_routers
from src.core.tracers import configure_tracer
from src.databases.pg import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управлять жизненным циклом приложения и подключениями к кешу."""
    await init_cache()
    yield
    await close_cache()


def create_app() -> FastAPI:
    """Создать и настроить экземпляр приложения FastAPI."""
    logging_config.dictConfig(logger.LOGGING)
    configure_tracer()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=("Сервис авторизации и аутентификации"),
        version="1.0.0",
        docs_url="/api/auth/openapi",
        openapi_url="/api/auth/openapi.json",
        lifespan=lifespan,
    )
    FastAPIInstrumentor.instrument_app(app, excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    register_middlewares(app)
    register_routers(app)

    return app
