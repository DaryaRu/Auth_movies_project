"""Fixture for tests /genres endpoints."""

import pytest_asyncio

from functional.settings import test_settings
from functional.testdata.es_mapping import GENRE_INDEX_SCHEMA
from functional.testdata.genres import GENRES_DATA


@pytest_asyncio.fixture(scope="session", autouse=True)
async def genre_data(es_write_data):
    """Load genre test data into Elasticsearch."""
    await es_write_data(
        test_settings.elastic_genres_index,
        GENRE_INDEX_SCHEMA,
        GENRES_DATA,
    )
