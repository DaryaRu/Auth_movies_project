"""Регистрация роутеров."""

from fastapi import FastAPI

from src.api.v1.short_links import router as short_links_router
from src.core.config import settings


def register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры приложения."""
    app.include_router(short_links_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}