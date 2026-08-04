"""Функциональные тесты эндпоинтов закладок."""

from http import HTTPStatus
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from tests.functional.utils.check_methods import (
    assert_status_return_json,
)
from tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestBookmarks:
    """Тесты эндпоинтов закладок."""

    URL = f"{test_settings.api_prefix}/bookmarks/"

    async def test_create_bookmark_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания закладки."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["movie_id"] == str(movie_id)

    async def test_delete_bookmark_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления закладки - закладка удалена."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
        }
        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        await assert_status_return_json(response, HTTPStatus.CREATED)

        response = await http_client.delete(
            f"{self.URL}{movie_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NO_CONTENT

    async def test_get_my_bookmarks_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения моих закладок."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
        }
        await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.get(
            f"{self.URL}my",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_create_bookmark_unauthorized(
        self,
        http_client: ClientSession,
    ):
        """Тест защиты эндпоинта: отсутствие токена авторизации."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
        }

        response = await http_client.post(self.URL, json=payload)
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_bookmark_not_found(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления несуществующей закладки."""
        movie_id = uuid4()

        response = await http_client.delete(
            f"{self.URL}{movie_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NOT_FOUND

    async def test_create_bookmark_duplicate(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест создания дубликата закладки - возвращается существующая."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
        }

        response1 = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data1 = await assert_status_return_json(response1, HTTPStatus.CREATED)

        response2 = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data2 = await assert_status_return_json(response2, HTTPStatus.CREATED)
        assert data1 is not None and isinstance(data1, dict)
        assert data2 is not None and isinstance(data2, dict)

        assert data1["id"] == data2["id"]
        assert data1["movie_id"] == data2["movie_id"]

    async def test_get_my_bookmarks_multiple(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест получения нескольких закладок."""
        movie_ids = [uuid4() for _ in range(3)]

        for movie_id in movie_ids:
            payload = {
                "movie_id": str(movie_id),
            }
            await http_client.post(
                self.URL,
                json=payload,
                headers={"Authorization": f"Bearer {generate_test_token}"},
            )

        response = await http_client.get(
            f"{self.URL}my",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["items"]) >= 3
