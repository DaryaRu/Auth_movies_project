"""Регистрация роутеров."""

from fastapi import FastAPI

from src.api.v1.notifications import router as notifications_router
from src.api.v1.templates import router as templates_router
from src.core.config import settings


def register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры приложения."""
    app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
    app.include_router(templates_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
