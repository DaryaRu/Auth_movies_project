import asyncio
from contextlib import asynccontextmanager

from monitorings.memory import memory_monitor
from core.dependiences import (
    init_dependencies,
    close_dependencies,
)


@asynccontextmanager
async def lifespan():
    await init_dependencies()
    memory_task = asyncio.create_task(
        memory_monitor()
    )
    yield
    memory_task.cancel()
    try:
        await memory_task
    except asyncio.CancelledError:
        pass
    await close_dependencies()
