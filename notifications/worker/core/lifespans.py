from contextlib import asynccontextmanager

from db.postgres import PostgreSQL


@asynccontextmanager
async def lifespan():
    await PostgreSQL.connect()
    yield
    await PostgreSQL.disconnect()
