"""Functional tests for /api/v1/genres endpoints."""

import pytest
from aiohttp import ClientSession

from functional.settings import test_settings
from functional.testdata.genres import GENRES_DATA
from tests.functional.src.cases import (
    DetailCase, ListCase, SortCase, ValidationErrorCase
)
from tests.functional.utils.check_methods import (
    assert_cache_isolated,
    assert_required_fields,
    assert_status_return_json,
)


GENRES_URL = f"{test_settings.api_prefix}/genres"

GENRE_ID = GENRES_DATA[0]["id"]
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


class TestGenreDetail:
    """Tests for GET /api/v1/genres/{genre_id}."""

    @pytest.mark.parametrize(
        "case",
        [
            DetailCase(GENRE_ID, 200, GENRE_ID, GENRES_DATA[0]["name"]),
            DetailCase(UNKNOWN_ID, 404),
        ],
    )
    async def test_genre_detail(
        self,
        http_client: ClientSession,
        case: DetailCase,
    ):
        response = await http_client.get(
            f"{GENRES_URL}/{case.entity_id}"
        )
        data = await assert_status_return_json(response, case.status_code)
        if response.status == 200:
            assert data["uuid"] == case.expected_uuid
            assert data["name"] == case.expected_name


class TestGenreDetailValidation:
    """Test UUID validation."""

    @pytest.mark.parametrize(
        "case",
        [
            DetailCase("true", 422),
            DetailCase("111", 422),
            DetailCase("00000000-0000-0000-0000-00000000000Z", 422),
        ],
    )
    async def test_invalid_uuid_returns_422(
        self,
        http_client: ClientSession,
        case: DetailCase,
    ):
        response = await http_client.get(f"{GENRES_URL}/{case.entity_id}")
        assert response.status == case.status_code


class TestGenreList:
    """Tests for GET /api/v1/genres/."""

    async def test_returns_200(self, http_client: ClientSession):
        response = await http_client.get(GENRES_URL)
        assert response.status == 200

    async def test_returns_all_genres(self, http_client: ClientSession):
        response = await http_client.get(GENRES_URL)
        data = await assert_status_return_json(response, 200)
        assert isinstance(data, list)
        assert len(data) == len(GENRES_DATA)

    async def test_response_has_required_fields(
        self, http_client: ClientSession
    ):
        response = await http_client.get(GENRES_URL)
        data = await assert_status_return_json(response, 200)
        genre = data[0]
        expected_fields = {"uuid", "name"}
        assert_required_fields(genre, expected_fields)


class TestGenreListSorting:
    """Tests for sort query parameter."""

    @pytest.mark.parametrize(
        "case",
        [
            SortCase(
                {"sort": "name"},
                200,
                sorted([g["name"] for g in GENRES_DATA]),
            ),
            SortCase(
                {"sort": "-name"},
                200,
                sorted([g["name"] for g in GENRES_DATA], reverse=True),
            ),
        ],
    )
    async def test_sort_returns_sorted_list(
        self,
        http_client: ClientSession,
        case: SortCase,
    ):
        response = await http_client.get(GENRES_URL, params=case.query)
        data = await assert_status_return_json(response, case.status_code)
        names = [g["name"] for g in data]
        assert names == case.expected_order

    @pytest.mark.parametrize(
        "case",
        [
            ValidationErrorCase({"sort": "id"}, 422),
            ValidationErrorCase({"sort": "uuid"}, 422),
            ValidationErrorCase({"sort": "invalid_field"}, 422),
        ]
    )
    async def test_invalid_sort_returns_422(
        self, http_client: ClientSession, case: ValidationErrorCase
    ):
        response = await http_client.get(GENRES_URL, params=case.query)
        assert response.status == case.status_code


class TestGenreCache:
    """Tests Redis cache."""

    @pytest.mark.parametrize(
        "url",
        [
            f"{GENRES_URL}/{GENRE_ID}",
            GENRES_URL,
        ],
    )
    async def test_repeated_request_responses_cache(
        self, http_client: ClientSession, url: str
    ):
        response_from_es = await http_client.get(url)
        first_body = await response_from_es.json()
        first_cache = response_from_es.headers.get("X-FastAPI-Cache")

        response_from_cache = await http_client.get(url)
        second_body = await response_from_cache.json()
        second_cache = response_from_cache.headers.get("X-FastAPI-Cache")

        assert first_body == second_body
        assert first_cache == "MISS"
        assert second_cache == "HIT"

    async def test_different_sort_params_cache(
        self, http_client: ClientSession
    ):
        response_sorted_asc = await http_client.get(
            GENRES_URL, params={"sort": "name"}
        )
        response_sorted_desc = await http_client.get(
            GENRES_URL, params={"sort": "-name"}
        )
        assert (
            await response_sorted_asc.json()
            != await response_sorted_desc.json()
        )

    async def test_different_pages_cache(self, http_client: ClientSession):
        response_first_page = await http_client.get(
            GENRES_URL, params={"page_size": 1, "page_number": 1}
        )
        response_second_page = await http_client.get(
            GENRES_URL, params={"page_size": 1, "page_number": 2}
        )
        data_first_page = await assert_status_return_json(
            response_first_page, 200
        )
        data_second_page = await assert_status_return_json(
            response_second_page, 200
        )
        assert data_first_page != data_second_page

    @pytest.mark.parametrize(
        'url_1, url_2',
        [
            (
                f"{GENRES_URL}/{GENRES_DATA[0]['id']}/",
                f"{GENRES_URL}/{GENRES_DATA[1]['id']}/",
            ),
            (
                f"{GENRES_URL}/?page_number=1&page_size=5",
                f"{GENRES_URL}/?page_number=1&page_size=10"
            ),
        ],
    )
    async def test_cache_isolated_by_query(
        self,
        http_client: ClientSession,
        url_1: str,
        url_2: str,
    ):
        await assert_cache_isolated(http_client, url_1, url_2)


class TestGenreListPaginationValidation:
    """Tests for pagination query parameters."""

    @pytest.mark.parametrize(
        "case",
        [
            ValidationErrorCase({"page_number": 0}, 422),
            ValidationErrorCase({"page_number": -1}, 422),
            ValidationErrorCase({"page_number": -100}, 422),
            ValidationErrorCase({"page_size": 0}, 422),
            ValidationErrorCase({"page_size": -1}, 422),
            ValidationErrorCase({"page_size": 101}, 422),
            ValidationErrorCase({"page_size": 1000}, 422),
            ValidationErrorCase({"page_number": "abc"}, 422),
        ],
    )
    async def test_invalid_pagination_returns_422(
        self,
        http_client: ClientSession,
        case: ValidationErrorCase,
    ):
        response = await http_client.get(GENRES_URL, params=case.query)
        assert response.status == case.status_code

    @pytest.mark.parametrize(
        "case",
        [
            ListCase({"page_size": 1}, 200, length=1),
            ListCase({"page_size": 100}, 200),
            ListCase({"page_number": 9999}, 200, body=[]),
        ],
    )
    async def test_valid_pagination_returns_200(
        self,
        http_client: ClientSession,
        case: ListCase,
    ):
        response = await http_client.get(GENRES_URL, params=case.query)
        data = await assert_status_return_json(response, case.status_code)
        if case.length is not None:
            assert len(data) == case.length
        if case.body is not None:
            assert data == case.body
