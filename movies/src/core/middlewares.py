import logging
import time
from logging import config as logging_config

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from core import config
from core import logger

logging_config.dictConfig(logger.LOGGING)


async def tracing_middleware(request: Request, call_next):
    request_id = request.headers.get('X-Request-Id')
    if not request_id and request.url.path not in config.EXCLUDED_PATHS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': {'error': 'X-Request-Id is required'}}
        )
    span = trace.get_current_span()
    if request_id and span.is_recording():
        span.set_attribute("request.id", request_id)
    response = await call_next(request)
    if request_id:
        response.headers["X-Request-Id"] = request_id
    return response


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


def register_middlewares(app: FastAPI):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOW_HOSTS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        ProxyHeadersMiddleware, trusted_hosts=config.ALLOW_HOSTS
        )

    app.middleware("http")(add_process_time_header)
    app.middleware("http")(tracing_middleware)
