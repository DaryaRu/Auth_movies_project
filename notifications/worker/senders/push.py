"""Push-отправитель: публикует уведомление в Redis Pub/Sub (канал push:{user_id}).

WS Gateway подписывается на push:* и ретранслирует через WebSocket подключённым клиентам.
"""

import json
from typing import Optional

import redis.asyncio as aioredis
from core.settings import settings


class PushSender:
    """Публикует push-уведомление в Redis Pub/Sub."""

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    async def start(self) -> None:
        """Подключиться к Redis (вызывается при старте воркера)."""
        self._redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False,
        )
        await self._redis.ping()

    async def stop(self) -> None:
        """Отключиться от Redis."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def send(
        self, delivery_address: str, subject: str | None, body: str
    ) -> None:
        """Опубликовать push-уведомление. delivery_address = user_id."""
        assert self._redis is not None, "PushSender not started"
        message = {
            "type": "notification",
            "user_id": delivery_address,
            "subject": subject,
            "body": body,
        }
        await self._redis.publish(
            f"push:{delivery_address}",
            json.dumps(message),
        )