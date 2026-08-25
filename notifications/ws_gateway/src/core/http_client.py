"""HTTP-клиент для вызовов к auth-service."""

import httpx

client: httpx.AsyncClient | None = None


def init() -> None:
    """Инициализировать HTTP-клиент."""
    global client
    client = httpx.AsyncClient()


async def close() -> None:
    """Закрыть HTTP-клиент."""
    global client
    if client is not None:
        await client.aclose()
        client = None
