from fastapi import FastAPI

from api.v1 import films, genres, persons


def register_routers(app: FastAPI) -> None:
    app.include_router(films.router, prefix="/api/v1/films", tags=["films"])
    app.include_router(genres.router, prefix="/api/v1/genres", tags=["genres"])
    app.include_router(
        persons.router, prefix="/api/v1/persons", tags=["persons"]
    )

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
