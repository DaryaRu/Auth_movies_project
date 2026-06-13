import hashlib
import logging
import sys
import time
from contextlib import asynccontextmanager
from logging import config as logging_config
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

sys.path.append(str(Path(__file__).parent.parent))

from src.api.v1.auth import router as auth_router
from src.api.v1.permissions import router as permissions_router
from src.api.v1.roles import router as roles_router
from src.core import logger
from src.core.config import settings
from src.databases import redis

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
    redis.redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    FastAPICache.init(
        RedisBackend(redis.redis),
        prefix="fastapi-cache",
        key_builder=key_builder,
    )
    logging.info("FastAPI cache initialized")
    yield
    await redis.redis.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Сервис авторизации и аутентификации"
    ),
    version="1.0.0",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
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


app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.ALLOWED_HOSTS.split(","))

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(roles_router, prefix=settings.API_V1_PREFIX)
app.include_router(permissions_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
