from fastapi import FastAPI

from src.api.v1.events import router as events_router
from src.core.config import settings


def register_routers(app: FastAPI) -> None:
    app.include_router(events_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
