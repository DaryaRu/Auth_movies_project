from typing import Awaitable, Callable

import pytest
import pytest_asyncio

from functional.testdata.es_mapping import PERSON_INDEX_SCHEMA
from functional.settings import test_settings


@pytest.fixture(scope='session')
def get_roles() -> Callable[[int], list[str]]:
    def inner(index: int) -> list[str]:
        match index % 4:
            case 0:
                return ["actor"]
            case 1:
                return ["director"]
            case 2:
                return ["writer"]
            case _:
                return ["actor", "director"]
    return inner


@pytest.fixture(scope='session')
def person_data(
    film_data: list[dict], get_roles: Callable[[int], list[str]]
) -> list[dict]:
    person_ids = [
        "5db9d84f-1a48-4637-8c5c-29f82f59f5d5",
        "7fefb90b-5a1a-4f68-9c1c-0d8c37b3d7e9",
        "c2d5d52e-7fcb-43d5-bcb6-8f94d3c7a6d1",
        "8b8d71ec-ec7f-4f88-9a8a-7c17fcb9cb1d",
        "1f5a2c76-c8d7-4973-b69e-c89f8d1e7d0f",
        "db61d3b7-5f41-4c8b-ae1f-4d7a42c69a5f",
        "36eaf8f4-7c42-4f6c-8f83-8dbf2c5c1b4e",
        "b1baf7a3-18d5-4bb5-bb95-6e82e5d6b26e",
        "79a07a34-bfd5-44c0-991c-fc64d56dbcc3",
        "4b92d6f8-2d89-4c7e-a8f0-9a34a2bc7d19",
        "f90c0b3d-43ef-4df6-9c3e-6a8f5cb6a7d2",
        "e73b12fd-3dc1-4e1b-a5db-1fbd35f7f7c4",
        "a42e5f97-f9a2-4d82-b8a5-3c3d0dcb8f42",
        "0d6f4e91-c6a9-4d59-92ea-6f7b95fbc8f0",
        "98a4d9bb-5fa3-4f1e-8d7a-0a8db96a4f3d",
        "6bcf0b91-6a3e-48a5-8dcb-73c5b9e7e1c0",
    ]
    film_ids = [
        "fc7d43d1-1d4a-4c0d-a41e-95c2a7a2df84",
        "9e8a5f64-2e14-42cf-b38d-2c3d4a7a8e17",
        "c0f4a3b5-59a7-4d3e-9b6a-5d7f9a3b1e26",
        "2a4f8e1b-7d3c-4e2a-b4f1-8d6a9c5b7e12",
        "d8c5b7e1-4f2a-43b6-8a7d-3c9e1f5b2a47",
        "31b5e7d9-8a4c-4f1d-b2e7-6a3c9d5f1e80",
        "f6a2d8b1-c4e5-47f3-9d1a-7b8c5e2f4a16",
        "7c3d1f5b-8a2e-4d6c-b7f9-1e3a5d8c2b44",
        "b9f4a2e6-3d1c-4f8a-a5b7-9c2d6e1f4a30",
        "e1d8c5a3-7f4b-4a2e-b6c9-5d1f8a3e2c74",
        "53f7b1a4-2d8e-4c6f-a9d1-7e3c5b2f8a60",
        "8d1a4c7f-5b2e-4f9c-b3d8-6a1e5c7f2b93",
        "a5c8e1d7-3f4b-4a2d-b9c6-1e7f5a3d2c48",
        "4e7b2a1d-8c5f-4d3a-a6e9-2b1c7f5d8a14",
        "cf2a5e8d-1b7c-4f4d-b3a9-6d1e8c5f2a31",
        "95d1a7c4-2f8b-4e3d-b6c5-1a9e7f2d4c88",
    ]
    names = [
        'Tom Hardy', 'Tom Hanks', 'Tom Holland', 'Thomas Shelby',
        'Emma Stone', 'Emma Watson', 'Emily Blunt', 'Emily Watson',
        'Chris Evans', 'Chris Hemsworth', 'Chris Pratt', 'Christian Bale',
        'Robert Downey Jr', 'Robert Pattinson', 'Rob Stark', 'Robin Williams',
    ]
    es_data = [{
        'id': person_ids[i],
        'name': names[i],
        'films': [
            {
                'id': film_ids[i],
                'roles': get_roles(i),
            }
        ],
    } for i in range(len(names))]
    film_person = film_data[0]["actors"][0]
    es_data.append({
        'id': film_person['id'],
        'name': film_person['name'],
        'films': [
            {'id': film['id'], 'roles': ['actor']}
            for film in film_data
        ]
    })
    return es_data


@pytest_asyncio.fixture(scope='session', autouse=True)
async def load_person_data_to_es(
    es_write_data: Callable[[str, dict, list[dict]], Awaitable[None],],
    person_data: list[dict]
) -> None:
    await es_write_data(
        test_settings.elastic_persons_index,
        PERSON_INDEX_SCHEMA,
        person_data,
    )
