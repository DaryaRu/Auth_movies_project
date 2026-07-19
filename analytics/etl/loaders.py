import asyncio
import logging
from collections import defaultdict

from core.settings import settings
from utils.backoff import async_backoff

logger = logging.getLogger(__name__)


class ClickHouseLoader:
    def __init__(
        self,
        client,
        batch_size: int = settings.ANALITYCS_ETL_BATCH_SIZE,
        flush_interval: float = settings.ANALITYCS_ETL_FLUSH_INTERVAL,
        max_buffer_size: int = settings.ANALITYCS_ETL_MAX_BUFFER_SIZE,
    ):
        self._client = client

        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_buffer_size = max_buffer_size

        self._buffers: dict[str, list[dict]] = defaultdict(list)

        self._condition = asyncio.Condition()

        self._closed = False
        self._flush_task: asyncio.Task | None = None

        self._inserted_rows = 0
        self._failed_inserts = 0

    async def start(self):
        self._flush_task = asyncio.create_task(
            self._flush_loop()
        )

        logger.info(
            "ClickHouse loader started"
        )

    async def stop(
        self,
        timeout: float = 30,
    ):
        logger.info(
            "Stopping ClickHouse loader"
        )

        self._closed = True

        async with self._condition:
            self._condition.notify()

        if self._flush_task:
            try:
                await asyncio.wait_for(
                    self._flush_task,
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "Loader shutdown timeout"
                )

    async def add(
        self,
        table: str,
        row: dict,
    ):
        async with self._condition:
            buffer = self._buffers[table]

            if len(buffer) >= self._max_buffer_size:
                raise RuntimeError(
                    f"Buffer overflow for table {table}"
                )

            buffer.append(row)

            buffer_size = len(buffer)

            if buffer_size >= self._batch_size:
                self._condition.notify()

            logger.debug(
                "Buffer size for %s: %s",
                table,
                buffer_size,
            )

    async def _flush_loop(self):
        while not self._closed:
            try:
                async with self._condition:
                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=self._flush_interval,
                        )
                    except TimeoutError:
                        pass

                    batches = self._get_batches()

                for table, batch in batches:
                    await self._insert_with_retry(
                        table,
                        batch,
                    )

            except Exception:
                logger.exception(
                    "Flush loop error"
                )

                await asyncio.sleep(1)

        await self._flush_remaining()

    def _get_batches(
        self,
    ) -> list[tuple[str, list[dict]]]:
        batches = []

        for table, buffer in self._buffers.items():
            if not buffer:
                continue

            batches.append(
                (
                    table,
                    buffer[: self._batch_size],
                )
            )

            del buffer[: self._batch_size]

        return batches

    async def _flush_remaining(self):
        batches = self._get_batches()

        for table, batch in batches:
            await self._insert_with_retry(
                table,
                batch,
            )

    @async_backoff(
        start_sleep_time=1,
        factor=2,
        border_sleep_time=30,
        max_attempts=5,
    )
    async def _insert(
        self,
        table: str,
        batch: list[dict],
    ):
        print(batch)
        await self._client.execute(
            f"""
            INSERT INTO {table}
            FORMAT JSONEachRow
            """,
            *batch,
        )

    async def _insert_with_retry(
        self,
        table: str,
        batch: list[dict],
    ):
        try:
            await self._insert(
                table,
                batch,
            )

            self._inserted_rows += len(batch)

            logger.info(
                "Inserted %s rows into %s",
                len(batch),
                table,
            )

        except Exception:
            self._failed_inserts += 1

            logger.exception(
                "Failed insert after retries: %s",
                table,
            )

            async with self._condition:
                buffer = self._buffers[table]

                if (
                    len(buffer) + len(batch)
                    <= self._max_buffer_size
                ):
                    buffer[0:0] = batch
                else:
                    logger.error(
                        "Dropping batch because buffer overflow: %s rows",
                        len(batch),
                    )
