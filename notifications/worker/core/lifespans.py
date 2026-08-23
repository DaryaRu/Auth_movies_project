from contextlib import asynccontextmanager

from db.postgres import PostgreSQL
from senders import SENDERS


@asynccontextmanager
async def lifespan():
    await PostgreSQL.connect()

    for sender in SENDERS.values():
        if hasattr(sender, "start"):
            await sender.start()

    yield

    for sender in SENDERS.values():
        if hasattr(sender, "stop"):
            await sender.stop()

    await PostgreSQL.disconnect()
