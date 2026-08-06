"""Функциональные тесты эндпоинтов лайков."""

from http import HTTPStatus
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from tests.functional.utils.check_methods import (
    assert_status_return_json,
)
from tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestLikes:
    """Тесты эндпоинтов лайков."""

    URL = f"{test_settings.api_prefix}/likes/"

    async def test_create_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания лайка (оценки 10)."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "rating": 10,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["movie_id"] == str(movie_id)
        assert data["rating"] == 10

    async def test_create_dislike_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания дизлайка (оценки 0)."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "rating": 0,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["movie_id"] == str(movie_id)
        assert data["rating"] == 0

    async def test_update_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест обновления лайка (с 10 на 0)."""
        movie_id = uuid4()

        like_payload = {
            "movie_id": str(movie_id),
            "rating": 10,
        }
        response = await http_client.post(
            self.URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        await assert_status_return_json(response, HTTPStatus.CREATED)

        dislike_payload = {
            "movie_id": str(movie_id),
            "rating": 0,
        }
        response = await http_client.post(
            self.URL,
            json=dislike_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["rating"] == 0

    async def test_delete_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления лайка - лайк удален."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
            "rating": 10,
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

    async def test_get_my_likes_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения моих лайков."""
        movie_id = uuid4()
        
        payload = {
            "movie_id": str(movie_id),
            "rating": 10,
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

    async def test_get_movie_likes_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения лайков фильма."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
            "rating": 10,
        }
        await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.get(
            f"{self.URL}movie/{movie_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_create_like_unauthorized(
        self,
        http_client: ClientSession,
    ):
        """Тест защиты эндпоинта: отсутствие токена авторизации."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "rating": 10,
        }

        response = await http_client.post(self.URL, json=payload)
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_like_not_found(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления несуществующего лайка."""
        movie_id = uuid4()

        response = await http_client.delete(
            f"{self.URL}{movie_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NOT_FOUND

    async def test_create_like_validation_error(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест валидации: некорректный рейтинг."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "rating": 15,  # rating должен быть от 0 до 10
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY