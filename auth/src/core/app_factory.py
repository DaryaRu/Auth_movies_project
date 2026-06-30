from contextlib import asynccontextmanager
from logging import config as logging_config

from fastapi import FastAPI
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from slowapi.errors import RateLimitExceeded

from src.core import logger
from src.core.cache import close_cache, init_cache
from src.core.config import settings
from src.core.middlewares import register_middlewares
from src.core.routers import register_routers
from src.core.tracers import configure_tracer
from src.core.limiter import limiter, rate_limit_exceeded_handler
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
        docs_url=settings.OPENAPI_URL,
        openapi_url=settings.OPENAPI_SCHEMA_URL,
        lifespan=lifespan,
    )

    limiter.storage_uri = settings.REDIS_LIMITER_URL
    app.state.limiter = limiter

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    FastAPIInstrumentor.instrument_app(app, excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS)
    AioHttpClientInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    register_middlewares(app)
    register_routers(app)

    return app
