import hashlib
import logging
import time
from contextlib import asynccontextmanager
from logging import config as logging_config
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from elastic_transport import ConnectionError as ESConnectionError
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse
from fastapi_cache import FastAPICache
from db.redis import FaultTolerantRedisBackend
from redis.asyncio import Redis
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api.v1 import films, genres, persons
from core import config
from core import logger
from db import elastic, redis

logging_config.dictConfig(logger.LOGGING)


def key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> str:
    url = str(request.url) if request else ""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sorted_query = urlencode(sorted(query.items()))
    normalized = f"{parsed.path}?{sorted_query}"
    cache_key = hashlib.md5(normalized.encode()).hexdigest()
    return f"{namespace}:{cache_key}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
    FastAPICache.init(
        FaultTolerantRedisBackend(redis.redis),
        prefix="fastapi-cache",
        key_builder=key_builder,
    )
    logging.info("FastAPI cache initialized")
    elastic.es = AsyncElasticsearch(
        hosts=[f"http://{config.ELASTIC_HOST}:{config.ELASTIC_PORT}"]
    )
    yield
    await redis.redis.close()
    await elastic.es.close()


app = FastAPI(
    title=config.PROJECT_NAME,
    description=(
        "Информация о фильмах, жанрах и людях, "
        "участвовавших в создании произведения"
    ),
    version="1.0.0",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware для измерения времени выполнения запроса"""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logging.info(
        f"Request: {request.method} {request.url.path} "
        f"Completed in {process_time:.4f} seconds "
        f"Status: {response.status_code}"
    )
    return response


app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOW_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=config.ALLOW_HOSTS)

app.include_router(films.router, prefix="/api/v1/films", tags=["films"])
app.include_router(genres.router, prefix="/api/v1/genres", tags=["genres"])
app.include_router(persons.router, prefix="/api/v1/persons", tags=["persons"])


@app.exception_handler(ESConnectionError)
async def es_unavailable_handler(request: Request, exc: ESConnectionError):
    return ORJSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "search service unavailable"},
    )


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
