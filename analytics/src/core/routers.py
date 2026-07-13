from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}
