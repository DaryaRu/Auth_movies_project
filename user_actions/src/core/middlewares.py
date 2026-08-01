"""Middleware для приложения."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings


def register_middlewares(app: FastAPI) -> None:
    """Регистрирует все middleware приложения."""
    origins = settings.ORIGINS.split(",") if settings.ORIGINS != "*" else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
