from functools import wraps
import asyncio
import logging
import random
import traceback


def backoff(
    start_sleep_time=0.1,
    factor=2,
    border_sleep_time=10,
    jitter=0.1,
    max_retries=3,
    exceptions=(Exception,),
):
    """
    Функция для повторного выполнения функции через некоторое время,
    если возникла ошибка.
    Использует наивный экспоненциальный рост времени повтора (factor)
    до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * (factor ^ n), если t < border_sleep_time
        t = border_sleep_time, иначе
    :param start_sleep_time: начальное время ожидания
    :param factor: во сколько раз нужно увеличивать время ожидания
        на каждой итерации
    :param border_sleep_time: максимальное время ожидания
    :return: результат выполнения функции
    """

    def func_wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            sleep_time = start_sleep_time
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_retries:
                        raise
                    logging.error(
                        f"Attempt {attempt + 1}/{max_retries + 1}\n"
                        f"Тип ошибки: {type(e).__name__}\n"
                        f"Описание: {e}\n"
                        f"Трассировка:\n{traceback.format_exc()}\n"
                    )
                    noise = random.normalvariate(0, sleep_time * jitter)
                    sleep_with_jitter = sleep_time + noise
                    sleep_with_jitter = max(0, sleep_with_jitter)
                    sleep_with_jitter = min(
                        sleep_with_jitter, border_sleep_time
                    )
                    await asyncio.sleep(sleep_with_jitter)
                    sleep_time = min(sleep_time * factor, border_sleep_time)
                    attempt += 1

        return inner

    return func_wrapper
