from logging import config as logging_config

from elastic_transport import ConnectionError as ESConnectionError
from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.aiohttp_client import (
    AioHttpClientInstrumentor,
)
from opentelemetry.instrumentation.elasticsearch import (
    ElasticsearchInstrumentor,
)
from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,
)

from core import config, logger
from core.lifespan import lifespan
from core.middlewares import register_middlewares
from core.routers import register_routers
from core.tracers import configure_tracer


def create_app() -> FastAPI:
    logging_config.dictConfig(logger.LOGGING)
    configure_tracer()

    app = FastAPI(
        title=config.PROJECT_NAME,
        description=(
            "Информация о фильмах, жанрах и людях, "
            "участвовавших в создании произведения"
        ),
        version="1.0.0",
        docs_url="/api/movies/openapi",
        openapi_url="/api/movies/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    FastAPIInstrumentor.instrument_app(
        app, excluded_urls=config.OTEL_PYTHON_FASTAPI_EXCLUDED_URLS
    )
    AioHttpClientInstrumentor().instrument()
    ElasticsearchInstrumentor().instrument()

    register_middlewares(app)
    register_routers(app)

    @app.exception_handler(ESConnectionError)
    async def es_unavailable_handler(request: Request, exc: ESConnectionError):
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "search service unavailable"},
        )

    return app
