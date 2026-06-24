"""Functional tests for empty Elasticsearch indices."""

from aiohttp import ClientSession

from functional.settings import test_settings
from tests.functional.utils.check_methods import assert_status_return_json

FILMS_URL = f"{test_settings.api_prefix}/films"
GENRES_URL = f"{test_settings.api_prefix}/genres"
PERSONS_URL = f"{test_settings.api_prefix}/persons"
UNKNOWN_UUID = "00000000-0000-0000-0000-000000000000"


class TestEmptyFilms:
    """Film endpoints return empty results when ES has no data."""

    async def test_film_list_returns_empty(self, http_client: ClientSession):
        """GET /films returns empty list when no films in ES."""
        response = await http_client.get(FILMS_URL)
        data = await assert_status_return_json(response, 200)
        assert data == []

    async def test_film_search_returns_empty(self, http_client: ClientSession):
        """GET /films/search returns empty list when no films in ES."""
        response = await http_client.get(
            f"{FILMS_URL}/search", params={"query": "anything"}
        )
        data = await assert_status_return_json(response, 200)
        assert data == []

    async def test_film_detail_returns_404(self, http_client: ClientSession):
        """GET /films/{id} returns 404 when no films in ES."""
        response = await http_client.get(f"{FILMS_URL}/{UNKNOWN_UUID}")
        await assert_status_return_json(response, 404)


class TestEmptyGenres:
    """Genre endpoints return empty results when ES has no data."""

    async def test_genre_list_returns_empty(self, http_client: ClientSession):
        """GET /genres returns empty list when no genres in ES."""
        response = await http_client.get(GENRES_URL)
        data = await assert_status_return_json(response, 200)
        assert data == []

    async def test_genre_detail_returns_404(self, http_client: ClientSession):
        """GET /genres/{id} returns 404 when no genres in ES."""
        response = await http_client.get(f"{GENRES_URL}/{UNKNOWN_UUID}")
        await assert_status_return_json(response, 404)


class TestEmptyPersons:
    """Person endpoints return empty results when ES has no data."""

    async def test_person_list_returns_empty(self, http_client: ClientSession):
        """GET /persons returns empty list when no persons in ES."""
        response = await http_client.get(PERSONS_URL)
        data = await assert_status_return_json(response, 200)
        assert data == []

    async def test_person_search_returns_empty(
        self, http_client: ClientSession
    ):
        """GET /persons/search returns empty list when no persons in ES."""
        response = await http_client.get(
            f"{PERSONS_URL}/search", params={"query": "anyone"}
        )
        data = await assert_status_return_json(response, 200)
        assert data == []

    async def test_person_detail_returns_404(self, http_client: ClientSession):
        """GET /persons/{id} returns 404 when no persons in ES."""
        response = await http_client.get(f"{PERSONS_URL}/{UNKNOWN_UUID}")
        await assert_status_return_json(response, 404)

    async def test_person_films_returns_404(self, http_client: ClientSession):
        """GET /persons/{id}/film returns 404 when person does not exist."""
        response = await http_client.get(
            f"{PERSONS_URL}/{UNKNOWN_UUID}/film"
        )
        await assert_status_return_json(response, 404)
