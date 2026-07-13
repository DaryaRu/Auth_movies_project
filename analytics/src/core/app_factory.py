from contextlib import asynccontextmanager
from logging import config as logging_config

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from src.core import logger
from src.core.config import settings
from src.core.middlewares import register_middlewares
from src.core.routers import register_routers
from src.core.tracers import configure_tracer


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    logging_config.dictConfig(logger.LOGGING)
    configure_tracer()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Сервис сбора аналитики пользователей",
        version="1.0.0",
        docs_url=settings.OPENAPI_URL,
        openapi_url=settings.OPENAPI_SCHEMA_URL,
        lifespan=lifespan,
    )

    FastAPIInstrumentor.instrument_app(app, excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()

    register_middlewares(app)
    register_routers(app)

    return app
