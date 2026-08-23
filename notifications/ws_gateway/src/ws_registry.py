"""In-memory реестр WebSocket-соединений и диспетчер push-уведомлений."""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# user_id -> set of active WebSocket connections
_connections: dict[str, set[WebSocket]] = defaultdict(set)


def register(user_id: str, ws: WebSocket) -> None:
    """Зарегистрировать WebSocket-соединение пользователя."""
    _connections[user_id].add(ws)
    logger.info(f"WS connected: user={user_id}, total={len(_connections[user_id])}")


def unregister(user_id: str, ws: WebSocket) -> None:
    """Удалить WebSocket-соединение пользователя."""
    _connections[user_id].discard(ws)
    if not _connections[user_id]:
        del _connections[user_id]
    logger.info(f"WS disconnected: user={user_id}")


def get_connection_count(user_id: str) -> int:
    """Количество активных соединений пользователя."""
    return len(_connections.get(user_id, set()))


async def _send_to_ws(ws: WebSocket, payload: str) -> bool:
    """Отправить payload одному WS. Возвращает False, если соединение мёртвое."""
    try:
        await ws.send_text(payload)
        return True
    except Exception:
        return False


async def dispatch_push(user_id: str, message: dict) -> bool:
    """Отправить push-уведомление всем подключённым WS конкретного пользователя.

    Отправка параллельная (asyncio.gather), медленный клиент не блокирует остальных.
    Возвращает True, если хотя бы одно соединение получило сообщение.
    """
    connections = _connections.get(user_id)
    if not connections:
        return False

    conns = list(connections)
    payload = json.dumps(message)
    results = await asyncio.gather(
        *(_send_to_ws(ws, payload) for ws in conns),
        return_exceptions=True,
    )

    delivered = False
    for ws, result in zip(conns, results, strict=True):
        if result is True:
            delivered = True
        else:
            if isinstance(result, Exception):
                logger.warning(f"WS send failed for user={user_id}: {result}")
            _connections[user_id].discard(ws)

    return delivered
