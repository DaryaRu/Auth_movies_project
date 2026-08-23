"""Redis Pub/Sub listener для push-уведомлений.

Слушает каналы push:* и диспатчит сообщения через WebSocket-реестр.
При обрыве соединения — автоматический reconnect с задержкой.
"""

import asyncio
import json
import logging

from src.core import redis
from src.ws_registry import dispatch_push

logger = logging.getLogger(__name__)

_REDIS_RECONNECT_DELAY: float = 5.0


async def _dispatch_message(user_id: str, payload: dict) -> None:
    """Диспатчит одно push-сообщение (выполняется параллельно с другими)."""
    delivered = await dispatch_push(user_id, payload)
    if not delivered:
        logger.debug(f"No active WS for user={user_id}, push dropped")


async def _redis_pubsub_listener() -> None:
    """Background-задача: слушает Redis Pub/Sub канал push:* и диспатчит через WS.

    Каждое сообщение обрабатывается в отдельной task, чтобы медленный
    dispatch не блокировал приём следующих сообщений из Redis.
    При обрыве соединения — автоматический reconnect с задержкой.
    """
    tasks: set[asyncio.Task] = set()

    try:
        while True:
            pubsub = redis.redis.pubsub()
            try:
                await pubsub.psubscribe("push:*")
                logger.info("Redis Pub/Sub listener started (pattern: push:*)")

                async for message in pubsub.listen():
                    if message["type"] != "pmessage":
                        continue
                    channel: str = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    data: str = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]

                    user_id = channel.removeprefix("push:")
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from Redis channel {channel}: {data[:200]}")
                        continue

                    task = asyncio.create_task(_dispatch_message(user_id, payload))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    f"Redis Pub/Sub connection lost: {exc}, "
                    f"reconnecting in {_REDIS_RECONNECT_DELAY}s"
                )
                await asyncio.sleep(_REDIS_RECONNECT_DELAY)
            finally:
                try:
                    await pubsub.punsubscribe()
                    await pubsub.close()
                except Exception:
                    pass
    except asyncio.CancelledError:
        pass
    finally:
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Redis Pub/Sub listener stopped")


def start() -> asyncio.Task:
    """Запустить Pub/Sub listener как background-задачу."""
    return asyncio.create_task(_redis_pubsub_listener())


async def stop(task: asyncio.Task) -> None:
    """Остановить Pub/Sub listener."""
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass