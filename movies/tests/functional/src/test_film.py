"""Functional tests for /api/v1/films endpoints."""

import pytest
from aiohttp import ClientSession

from functional.settings import test_settings
from functional.testdata.films import (
    FILMS_DATA,
    TEST_GENRE_ID,
    TEST_PERSON_ID,
    FILM_DATA_LIST_LENGTH,
)
from tests.functional.src.cases import (
    DetailCase, ListCase, ValidationErrorCase, SearchCase, SortCase
)
from tests.functional.utils.check_methods import (
    assert_cache_isolated, assert_required_fields, assert_status_return_json
)


FILMS_URL = f"{test_settings.api_prefix}/films"
PERSON_FILMS_URL = f"{test_settings.api_prefix}/persons/{TEST_PERSON_ID}/film"
UNKNOWN_UUID = "00000000-0000-0000-0000-000000000000"
INVALID_UUID = "not-a-valid-uuid-123"
ERR_FILM_NOT_FOUND = {"detail": "film not found"}
ERR_PERSON_NOT_FOUND = {"detail": "person not found"}
PAGE_SIZE = 100


class TestFilmDetail:
    """Tests for GET /api/v1/films/{film_id}."""

    @pytest.mark.parametrize(
        "case",
        [
            DetailCase(FILMS_DATA[0]["id"], 200),
            DetailCase(UNKNOWN_UUID, 404),
            DetailCase(INVALID_UUID, 422),
        ],
    )
    async def test_film_detail(
        self,
        http_client: ClientSession,
        case: DetailCase,
    ):
        response = await http_client.get(f"{FILMS_URL}/{case.entity_id}")
        data = await assert_status_return_json(response, case.status_code)
        if response.status == 200:
            expected_fields = {
                "uuid",
                "title",
                "imdb_rating",
                "description",
                "creation_date",
                "directors",
                "actors",
                "writers",
                "genre",
            }
            assert_required_fields(data, expected_fields)
            assert isinstance(data["title"], str)
            assert (
                isinstance(data["imdb_rating"], (float, int))
                or data["imdb_rating"] is None
            )
            assert (
                isinstance(data["description"], str)
                or data["description"] is None
            )

            expected_film = FILMS_DATA[0]
            assert data["uuid"] == expected_film["id"]
            assert data["title"] == expected_film["title"]
            assert data["imdb_rating"] == expected_film["imdb_rating"]
            assert data["description"] == expected_film["description"]

            assert len(data["genre"]) == 1
            genre = data["genre"][0]
            assert isinstance(genre, dict)
            assert "uuid" in genre and "name" in genre
            assert genre["uuid"] == TEST_GENRE_ID
            assert genre["name"] == "Action"

            assert len(data["actors"]) == 1
            actor = data["actors"][0]
            assert isinstance(actor, dict)
            assert "uuid" in actor and "full_name" in actor
            assert actor["full_name"] == "Ann"

            assert isinstance(data["directors"], list)
            assert isinstance(data["writers"], list)

        elif response.status == 404:
            assert data == ERR_FILM_NOT_FOUND


class TestFilmDetailValidation:
    """Test UUID validation film detail query data."""

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
        response = await http_client.get(f"{FILMS_URL}/{case.entity_id}")
        assert response.status == case.status_code


class TestFilmList:
    """Tests for GET /api/v1/films."""

    async def test_film_list_returns_200(self, http_client: ClientSession):
        response = await http_client.get(FILMS_URL)
        assert response.status == 200

    async def test_returns_all_films(self, http_client: ClientSession):
        response = await http_client.get(
            FILMS_URL, params={"page_size": PAGE_SIZE}
        )
        data = await assert_status_return_json(response, 200)
        assert isinstance(data, list)
        assert len(data) == len(FILMS_DATA)

    async def test_films_list_film_info(self, http_client: ClientSession):
        response = await http_client.get(FILMS_URL)
        data = await assert_status_return_json(response, 200)
        assert isinstance(data, list)
        assert len(data) > 0

        first_film = data[0]
        expected_fields = {"uuid", "title", "imdb_rating"}
        assert_required_fields(first_film, expected_fields)

        assert isinstance(first_film["title"], str)
        assert (
            isinstance(first_film["imdb_rating"], (float, int))
            or first_film["imdb_rating"] is None
        )

        title_str = first_film.get("title", "")
        position = int(title_str.replace("The Star Part", "").strip())
        expected_film = FILMS_DATA[position]

        assert first_film["uuid"] == expected_film["id"]
        assert first_film["title"] == expected_film["title"]
        assert first_film["imdb_rating"] == expected_film["imdb_rating"]

    async def test_films_list_filter_by_genre(
        self, http_client: ClientSession
    ):
        response = await http_client.get(
            FILMS_URL,
            params={"filter[genre]": TEST_GENRE_ID, "page_size": PAGE_SIZE},
        )
        data = await assert_status_return_json(response, 200)

        assert isinstance(data, list)
        assert len(data) == len(FILMS_DATA)

    async def test_films_list_invalid_genre_uuid(
        self, http_client: ClientSession
    ):
        response = await http_client.get(
            FILMS_URL, params={"filter[genre]": INVALID_UUID}
        )
        assert response.status == 422


class TestFilmListSorting:
    """Tests for sort query parameter in films endpoint."""

    @pytest.mark.parametrize(
        "case",
        [
            SortCase(
                {"sort": "imdb_rating", "page_size": PAGE_SIZE},
                200,
                sorted([f["imdb_rating"] for f in FILMS_DATA]),
            ),
            SortCase(
                {"sort": "-imdb_rating", "page_size": PAGE_SIZE},
                200,
                sorted([f["imdb_rating"] for f in FILMS_DATA], reverse=True),
            ),
        ],
    )
    async def test_sort_returns_sorted_film_list(
        self,
        http_client: ClientSession,
        case: SortCase,
    ):
        response = await http_client.get(FILMS_URL, params=case.query)
        data = await assert_status_return_json(response, case.status_code)
        ratings = [f["imdb_rating"] for f in data]
        assert ratings == case.expected_order

    @pytest.mark.parametrize(
        "case",
        [
            ValidationErrorCase({"sort": "id"}, 422),
            ValidationErrorCase({"sort": "description"}, 422),
            ValidationErrorCase({"sort": "invalid_field"}, 422),
        ]
    )
    async def test_invalid_sort_returns_422(
        self, http_client: ClientSession, case: ValidationErrorCase
    ):
        response = await http_client.get(FILMS_URL, params=case.query)
        assert response.status == case.status_code


class TestFilmListPaginationValidation:
    """Tests for pagination query parameters."""

    @pytest.mark.parametrize(
        "case",
        [
            ValidationErrorCase({"page_number": 0}, 422),
            ValidationErrorCase({"page_number": -1}, 422),
            ValidationErrorCase({"page_size": 0}, 422),
            ValidationErrorCase({"page_size": -1}, 422),
            ValidationErrorCase({"page_size": 101}, 422),
            ValidationErrorCase({"page_size": 1000000}, 422),
            ValidationErrorCase({"page_number": "abc"}, 422),
        ],
    )
    async def test_invalid_pagination_returns_422(
        self,
        http_client: ClientSession,
        case: ValidationErrorCase
    ):
        response = await http_client.get(FILMS_URL, params=case.query)
        assert response.status == case.status_code

    @pytest.mark.parametrize(
        "case",
        [
            ListCase(query={"page_size": 1}, status_code=200, length=1),
            ListCase(
                query={"page_size": 100},
                status_code=200,
                length=FILM_DATA_LIST_LENGTH,
            ),
            ListCase(
                query={},
                status_code=200,
                length=test_settings.pagination_default_page_size,
            ),
            ListCase(query={"page_number": 9999}, status_code=200, body=[]),
        ],
    )
    async def test_valid_pagination_returns_200(
        self,
        http_client: ClientSession,
        case: ListCase,
    ):
        response = await http_client.get(FILMS_URL, params=case.query)
        data = await assert_status_return_json(response, case.status_code)
        assert isinstance(data, list)

        if case.length is not None:
            assert len(data) <= case.length

        if case.body is not None:
            assert data == case.body


class TestFilmForPerson:
    """Tests for GET /api/v1/persons/{person_uuid}/film."""

    async def test_returns_200_for_valid_person(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.get(PERSON_FILMS_URL)
        assert response.status == 200

    async def test_returns_all_films_for_person(
        self, http_client: ClientSession
    ):
        response = await http_client.get(
            PERSON_FILMS_URL, params={"page_size": FILM_DATA_LIST_LENGTH}
        )
        data = await assert_status_return_json(response, 200)
        assert isinstance(data, list)
        assert len(data) == len(FILMS_DATA)

    async def test_response_models_validation(
        self, http_client: ClientSession
    ):
        response = await http_client.get(
            PERSON_FILMS_URL, params={"page_size": 1}
        )
        data = await assert_status_return_json(response, 200)
        assert len(data) > 0
        film = data[0]

        expected_fields = {"uuid", "title", "imdb_rating"}
        assert_required_fields(film, expected_fields)

        assert isinstance(film["title"], str)
        assert (
            isinstance(film["imdb_rating"], (float, int))
            or film["imdb_rating"] is None
        )

        title_str = film.get("title", "")
        position = int(title_str.replace("The Star Part", "").strip())

        expected_film = FILMS_DATA[position]
        assert film["uuid"] == expected_film["id"]

    async def test_unknown_person_returns_404(
        self, http_client: ClientSession
    ):
        url = f"{test_settings.api_prefix}/persons/{UNKNOWN_UUID}/film"
        response = await http_client.get(url)
        data = await assert_status_return_json(response, 404)
        assert data == ERR_PERSON_NOT_FOUND

    async def test_invalid_person_uuid_returns_422(
        self, http_client: ClientSession
    ):
        url = f"{test_settings.api_prefix}/persons/{INVALID_UUID}/film"
        response = await http_client.get(url)
        assert response.status == 422


class TestFilmCache:
    """Tests Redis cache for films endpoints."""

    @pytest.mark.parametrize(
        "url",
        [
            FILMS_URL,
            f"{FILMS_URL}/{FILMS_DATA[0]['id']}",
            f"{test_settings.api_prefix}/persons/{TEST_PERSON_ID}/film",
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
            FILMS_URL,
            params={"sort": "imdb_rating", "page_size": FILM_DATA_LIST_LENGTH},
        )
        response_sorted_desc = await http_client.get(
            FILMS_URL,
            params={
                "sort": "-imdb_rating",
                "page_size": FILM_DATA_LIST_LENGTH,
            },
        )

        assert (
            await response_sorted_asc.json()
            != await response_sorted_desc.json()
        )

    async def test_different_pages_cache(self, http_client: ClientSession):
        response_first_page = await http_client.get(
            FILMS_URL, params={"page_size": 1, "page_number": 1}
        )
        response_second_page = await http_client.get(
            FILMS_URL, params={"page_size": 1, "page_number": 2}
        )

        assert (
            await response_first_page.json()
            != await response_second_page.json()
        )

    async def test_different_genre_filters_cache(
        self, http_client: ClientSession
    ):

        response_action_genre = await http_client.get(
            FILMS_URL, params={"filter[genre]": TEST_GENRE_ID}
        )
        response_empty_genre = await http_client.get(
            FILMS_URL, params={"filter[genre]": UNKNOWN_UUID}
        )

        assert (
            await response_action_genre.json()
            != await response_empty_genre.json()
        )

    @pytest.mark.parametrize(
        'url_1, url_2',
        [
            (
                f"{FILMS_URL}/{FILMS_DATA[0]['id']}/",
                f"{FILMS_URL}/{FILMS_DATA[1]['id']}/",
            ),
            (f"{FILMS_URL}/search?query=star", f"{FILMS_URL}/search?query=6"),
            (
                f"{FILMS_URL}/?page_number=1&page_size=5",
                f"{FILMS_URL}/?page_number=1&page_size=10",
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


class TestFilmSearch:
    """Tests for GET /api/v1/films/search."""

    @pytest.mark.parametrize(
        "case",
        [
            SearchCase(
                {"query": "The Star", "page_size": 100},
                200,
                FILM_DATA_LIST_LENGTH,
            ),
            SearchCase({"query": "5"}, 200, 1),
            SearchCase({"query": "NonExistingFilm"}, 200, 0),
            SearchCase(
                {"query": "THE STAR", "page_size": 100},
                200,
                FILM_DATA_LIST_LENGTH
                ),
            SearchCase(
                {"query": "the star", "page_size": 100},
                200,
                FILM_DATA_LIST_LENGTH
                ),
            SearchCase(
                {"query": "ThE StAr", "page_size": 100},
                200,
                FILM_DATA_LIST_LENGTH
                ),
            SearchCase({"query": "5"}, 200, 1),
            SearchCase({"query": "NonExistingFilm"}, 200, 0),
            SearchCase({"query": "test", "page_number": 10001}, 200, 0),
        ],
    )
    @pytest.mark.asyncio
    async def test_film_search(
        self,
        http_client: ClientSession,
        case: SearchCase,
    ):
        response = await http_client.get(
            f"{FILMS_URL}/search", params=case.query
        )
        data = await assert_status_return_json(response, case.status_code)
        assert isinstance(data, list)
        assert len(data) == case.length

    @pytest.mark.parametrize(
        "case",
        [
            ValidationErrorCase({}, 422),
            ValidationErrorCase({"page_size": 10}, 422),
            ValidationErrorCase({"page_number": 1}, 422),

            ValidationErrorCase({"query": "test", "page_size": 0}, 422),
            ValidationErrorCase({"query": "test", "page_size": -1}, 422),
            ValidationErrorCase({"query": "test", "page_size": 10001}, 422),

            ValidationErrorCase({"query": "test", "page_number": 0}, 422),
            ValidationErrorCase({"query": "test", "page_number": -1}, 422),

            ValidationErrorCase({"query": "test", "page_size": "string"}, 422),
            ValidationErrorCase(
                {"query": "test", "page_number": "string"}, 422
                ),
        ],
    )
    @pytest.mark.asyncio
    async def test_film_search_ng(
        self,
        http_client: ClientSession,
        case: ValidationErrorCase,
    ):
        response = await http_client.get(
            f"{FILMS_URL}/search", params=case.query
        )

        await assert_status_return_json(
            response, case.status_code
            )
