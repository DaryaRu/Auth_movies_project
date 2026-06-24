from fastapi import FastAPI

from src.api.v1.auth import router as auth_router
from src.api.v1.oauth import router as oauth_router
from src.api.v1.permissions import router as permissions_router
from src.api.v1.roles import router as roles_router
from src.core.config import settings


def register_routers(app: FastAPI) -> None:
    """Подключить все роутеры приложения"""
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(oauth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(roles_router, prefix=settings.API_V1_PREFIX)
    app.include_router(permissions_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
