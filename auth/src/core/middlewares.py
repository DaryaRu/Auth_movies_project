import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.core.config import settings


def register_middlewares(app: FastAPI) -> None:
    """Зарегистрировать все middleware в приложении"""
    
    excluded_paths = {"/health", f"{settings.API_V1_PREFIX}/auth/openapi.json", f"{settings.API_V1_PREFIX}/jwt.key/"}

    @app.middleware('http')
    async def tracing_middlemare(request: Request, call_next):
        request_id = request.headers.get('X-Request-Id')
        if not request_id and request.url.path not in excluded_paths:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={'detail': {'error': 'X-Request-Id is required'}})
        span = trace.get_current_span()
        if request_id and span.is_recording():
            span.set_attribute("request.id", request_id)
        response = await call_next(request)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Middleware для измерения времени выполнения запроса"""
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            process_time = time.perf_counter() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            logging.info(
                f"Request: {request.method} {request.url.path} "
                f"Completed in {process_time:.4f} seconds "
                f"Status: {response.status_code}"
            )

    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS.split(",")
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        ProxyHeadersMiddleware, trusted_hosts=settings.ALLOWED_HOSTS.split(",")
    )
