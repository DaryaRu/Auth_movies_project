"""Retry failed operations with backoff."""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def backoff(
    start_sleep_time: float = 0.1,
    factor: int = 2,
    border_sleep_time: float = 10,
    max_retries: int = 50,
):
    def func_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for retry_number in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    delay = min(
                        start_sleep_time * (factor**retry_number),
                        border_sleep_time,
                    )
                    logger.exception(
                        "Temporary error in '%s', delay %.2fs",
                        func.__name__,
                        delay,
                    )
                    if retry_number < max_retries - 1:
                        time.sleep(delay)

            raise RuntimeError(
                f"{func.__name__} failed after {max_retries} retries"
            ) from last_exception

        return wrapper

    return func_wrapper
