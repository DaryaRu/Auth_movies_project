"""Общий httpx.AsyncClient для HTTP-вызовов к другим сервисам."""

import httpx


class HTTPClient:
    """Класс для управления общим httpx-клиентом."""

    client: httpx.AsyncClient | None = None

    @classmethod
    async def connect(cls) -> None:
        """Создать клиент с пулом соединений."""
        if cls.client is None:
            cls.client = httpx.AsyncClient()

    @classmethod
    async def disconnect(cls) -> None:
        """Закрыть клиент и все соединения в пуле."""
        if cls.client is not None:
            await cls.client.aclose()
            cls.client = None
