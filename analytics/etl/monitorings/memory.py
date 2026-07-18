import asyncio
import logging
import os

import psutil


logger = logging.getLogger(__name__)


async def memory_monitor(
    interval: int = 30,
):
    process = psutil.Process(
        os.getpid()
    )

    try:
        while True:
            memory_mb = (
                process.memory_info().rss
                / 1024
                / 1024
            )

            logger.info(
                f"Memory usage: {memory_mb} MB",
            )

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info(
            "Memory monitor stopped"
        )
        raise
