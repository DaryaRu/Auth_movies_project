import aiohttp
from aiochclient import ChClient

from core.settings import settings


class ClickHouseClient:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self.client: ChClient | None = None

    async def start(self):
        self._session = aiohttp.ClientSession()

        self.client = ChClient(
            self._session,
            url=settings.CLICKHOUSE_URL,
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB,
        )

    async def stop(self):
        if self._session:
            await self._session.close()
