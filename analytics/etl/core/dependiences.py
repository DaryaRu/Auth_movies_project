from db.clickhouse_db import ClickHouseClient
from loaders import ClickHouseLoader
from repositories.movie_views import MovieViewsRepository


clickhouse = ClickHouseClient()

loader = None
movie_views_repository = None


async def init_dependencies():
    global loader
    global movie_views_repository

    await clickhouse.start()

    from extractors import dlq_publisher

    loader = ClickHouseLoader(
        client=clickhouse.client,
        dlq_publisher=dlq_publisher,
    )

    await loader.start()

    movie_views_repository = MovieViewsRepository(
        loader=loader,
        client=clickhouse.client,
    )

    await movie_views_repository.create_table()


async def close_dependencies():
    await loader.stop()
    await clickhouse.stop()
