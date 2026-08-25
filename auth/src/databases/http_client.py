"""HTTP-клиент. Используется один клиент с пулом соединений на все приложение."""

from typing import Optional

import httpx

client: Optional[httpx.AsyncClient] = None


async def connect() -> None:
    """Создать клиент с пулом соединений."""
    global client
    if client is None:
        client = httpx.AsyncClient()


async def disconnect() -> None:
    """Закрыть клиент и все соединения в пуле."""
    global client
    if client is not None:
        await client.aclose()
        client = None
