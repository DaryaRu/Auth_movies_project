import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.core.config import settings


def register_middlewares(app: FastAPI) -> None:
    """Зарегистрировать все middleware в приложении"""

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
