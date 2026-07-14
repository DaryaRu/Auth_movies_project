from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.cache import close_cache, init_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    yield
    await close_cache()
