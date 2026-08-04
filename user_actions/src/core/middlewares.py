"""Middleware для приложения."""

import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.core.config import settings


def register_middlewares(app: FastAPI) -> None:
    """Регистрирует все middleware приложения."""
    excluded_paths = {
        "/health",
        settings.OPENAPI_URL,
        settings.OPENAPI_SCHEMA_URL,
    }

    @app.middleware("http")
    async def tracing_middleware(request: Request, call_next):
        """Middleware для добавления request_id в спан трассировки."""
        request_id = request.headers.get("X-Request-Id")
        if not request_id and request.url.path not in excluded_paths:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": {"error": "X-Request-Id is required"}},
            )
        span = trace.get_current_span()
        if request_id and span.is_recording():
            span.set_attribute("request.id", request_id)
        response = await call_next(request)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Middleware для добавления времени обработки в заголовки."""
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logging.info(
            "Request: %s %s Completed in %.4f seconds Status: %s",
            request.method,
            request.url.path,
            process_time,
            response.status_code,
        )
        return response

    origins = settings.ORIGINS.split(",") if settings.ORIGINS != "*" else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        ProxyHeadersMiddleware,  # type: ignore[arg-type]
        trusted_hosts=settings.ALLOWED_HOSTS.split(",") if settings.ALLOWED_HOSTS != "*" else ["*"],
    )
