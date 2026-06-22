"""Override autouse fixtures to keep ES empty."""

import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def load_film_data():
    pass


@pytest_asyncio.fixture(scope="session", autouse=True)
async def genre_data():
    pass


@pytest_asyncio.fixture(scope="session", autouse=True)
async def load_person_data_to_es():
    pass
