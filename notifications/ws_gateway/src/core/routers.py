"""Регистрация роутеров."""

from fastapi import FastAPI

from src.api.v1.websocket import router as ws_router


def register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры приложения."""
    app.include_router(ws_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}