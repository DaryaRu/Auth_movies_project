"""WebSocket-эндпоинт для push-уведомлений.

Клиент подключается: ws://host/api/v1/ws/notifications?token=<JWT>
Сервер верифицирует JWT (RS256, публичный ключ из auth-service),
подписывает на push-уведомления для этого пользователя.

Push-уведомления приходят через Redis Pub/Sub (канал push:{user_id}).
Каждый инстанс ws-gateway подписывается на все каналы push:* —
Redis доставляет сообщение на все инстансы, а dispatch_push
доставляет только тем, у кого есть активное WS-соединение.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.config import settings
from src.core.jwt_key import decode_token
from src.ws_registry import (
    get_connection_count,
    register,
    unregister,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_WS_MSG_RATE_LIMIT: int = 10


class _RateLimiter:
    """token bucket: max N сообщений в секунду."""

    def __init__(self, max_per_sec: int) -> None:
        self._max = max_per_sec
        self._tokens = float(max_per_sec)
        self._last_refill = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max, self._tokens + elapsed * self._max)
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """WebSocket для push-уведомлений.

    Подключение: ws://host/api/v1/ws/notifications?token=<JWT>
    Формат входящих сообщений: {"type": "ping"} → {"type": "pong"}
    Формат исходящих: {"type": "notification", "subject": "...", "body": "..."}
    """
    payload = await decode_token(token)
    if payload is None:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token payload")
        return

    if get_connection_count(user_id) >= settings.WS_MAX_CONNECTIONS_PER_USER:
        await websocket.close(code=1013, reason="Too many connections")
        return

    await websocket.accept()
    register(user_id, websocket)
    logger.info(f"WS connected: user={user_id}")

    rate_limiter = _RateLimiter(_WS_MSG_RATE_LIMIT)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_PING_INTERVAL_SEC,
                )
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.WS_PING_TIMEOUT_SEC,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"WS ping timeout for user={user_id}, closing")
                    await websocket.close(code=1001, reason="Ping timeout")
                    break
                # Если клиент ответил не pong, а обычным сообщением — обрабатываем ниже
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "pong":
                        continue
                except json.JSONDecodeError:
                    pass

            if not rate_limiter.allow():
                logger.warning(f"WS rate limit exceeded for user={user_id}, closing")
                await websocket.close(code=1008, reason="Rate limit exceeded")
                break
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(f"WS error for user={user_id}: {exc}")
    finally:
        unregister(user_id, websocket)
        logger.info(f"WS closed: user={user_id}")
