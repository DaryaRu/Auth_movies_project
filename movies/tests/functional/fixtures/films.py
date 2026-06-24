"""Fixture for tests /films endpoints."""

import pytest
import pytest_asyncio

from functional.settings import test_settings
from functional.testdata.es_mapping import (
    MOVIES_INDEX_SCHEMA,
)
from functional.testdata.films import FILMS_DATA


@pytest.fixture(scope='session')
def film_data() -> list[dict]:
    return FILMS_DATA


@pytest_asyncio.fixture(scope="session", autouse=True)
async def load_film_data(es_write_data):
    """Load films test data into Elasticsearch."""
    await es_write_data(
        test_settings.elastic_movies_index,
        MOVIES_INDEX_SCHEMA,
        FILMS_DATA,
    )
