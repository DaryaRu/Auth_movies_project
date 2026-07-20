import asyncio
import logging
import random
from functools import wraps


logger = logging.getLogger(__name__)


def async_backoff(
    start_sleep_time: float = 0.1,
    factor: int = 2,
    border_sleep_time: float = 10,
    jitter: float = 0.1,
    max_attempts: int = 5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            sleep_time = start_sleep_time

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.exception(
                            "Failed after %s attempts: %s",
                            attempt,
                            exc,
                        )
                        raise

                    noise = random.uniform(
                        -sleep_time * jitter,
                        sleep_time * jitter,
                    )

                    delay = min(
                        max(
                            sleep_time + noise,
                            0,
                        ),
                        border_sleep_time,
                    )

                    logger.warning(
                        "Attempt %s/%s failed: %s. Retry after %.2fs",
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )

                    await asyncio.sleep(delay)

                    sleep_time = min(
                        sleep_time * factor,
                        border_sleep_time,
                    )

        return wrapper

    return decorator
