"""Регистрация роутеров."""

from fastapi import FastAPI

from src.api.v1 import bookmarks_router, likes_router, review_likes_router, reviews_router
from src.core.config import settings


def register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры приложения."""
    api_prefix = f"{settings.API_V1_PREFIX}/user-actions"

    app.include_router(bookmarks_router, prefix=api_prefix)
    app.include_router(likes_router, prefix=api_prefix)
    app.include_router(review_likes_router, prefix=api_prefix)
    app.include_router(reviews_router, prefix=api_prefix)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
