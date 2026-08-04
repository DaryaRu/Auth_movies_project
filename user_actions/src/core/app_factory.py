"""Фабрика приложения."""

from logging import config as logging_config

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from slowapi.errors import RateLimitExceeded

from src.core import logger
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.limiter import limiter, rate_limit_exceeded_handler
from src.core.middlewares import register_middlewares
from src.core.routers import register_routers
from src.core.sentry import sentry_init
from src.core.tracers import configure_tracer


def create_app() -> FastAPI:
    """Создает и настраивает приложение FastAPI."""
    logging_config.dictConfig(logger.LOGGING)

    configure_tracer()
    sentry_init()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Сервис управления пользовательскими действиями: закладки, лайки, рецензии",
        version="1.0.0",
        docs_url=settings.OPENAPI_URL,
        openapi_url=settings.OPENAPI_SCHEMA_URL,
        lifespan=lifespan,
    )

    limiter.enabled = settings.ENVIRONMENT != "test"
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    register_middlewares(app)
    register_routers(app)

    FastAPIInstrumentor.instrument_app(app, excluded_urls=settings.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()

    return app
