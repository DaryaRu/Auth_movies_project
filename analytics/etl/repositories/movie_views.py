from typing import Any

from aiochclient import ChClient

from loaders import ClickHouseLoader


class MovieViewsRepository:
    TABLE = "movie_views_local"

    CREATE_TABLES = [
        """
        CREATE TABLE IF NOT EXISTS movie_views_local
        ON CLUSTER movie_cluster
        (
            user_id UUID,
            movie_id UUID,
            viewed_frame UInt32,
            movie_duration UInt32,
            event_time DateTime
        )
        ENGINE = ReplicatedMergeTree(
            '/clickhouse/tables/{shard}/movie_views_local',
            '{replica}'
        )
        ORDER BY (
            movie_id,
            event_time,
            user_id
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS movie_views
        ON CLUSTER movie_cluster
        AS movie_views_local
        ENGINE = Distributed(
            movie_cluster,
            default,
            movie_views_local,
            rand()
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
