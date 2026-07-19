import logging
from typing import Any

from aiochclient import ChClient

from loaders import ClickHouseLoader


class MovieViewsRepository:
    TABLE = "analytics.events_local"

    CREATE_TABLES = [
        """
        CREATE DATABASE IF NOT EXISTS analytics
        ON CLUSTER movie_cluster
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics.events_local
        ON CLUSTER movie_cluster
        (
            user_id UUID,
            event_type LowCardinality(String),
            object_id Nullable(UUID),
            payload String,
            event_time DateTime64(3, 'UTC'),
            created_at DateTime64(3, 'UTC') DEFAULT now64(3)
        )
        ENGINE = ReplicatedMergeTree(
            '/clickhouse/tables/{shard}/analytics/events_local',
            '{replica}'
        )
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (
            event_type,
            event_time,
            user_id
        )
        SETTINGS index_granularity = 8192
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics.events
        ON CLUSTER movie_cluster
        AS analytics.events_local
        ENGINE = Distributed(
            movie_cluster,
            analytics,
            events_local,
            cityHash64(user_id)
        )
        """
    ]

    def __init__(
        self,
        loader: ClickHouseLoader,
        client: ChClient,
    ):
        self._loader = loader
        self._client = client

    async def create_table(self):
        for query in self.CREATE_TABLES:
            await self._client.execute(query)

    async def save(
        self,
        row: dict[str, Any],
    ):
        await self._loader.add(
            self.TABLE,
            row,
        )
