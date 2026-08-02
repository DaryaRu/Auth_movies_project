"""Функциональные тесты эндпоинтов рецензий и лайков на рецензии."""

from http import HTTPStatus
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from user_actions.tests.functional.utils.check_methods import (
    assert_status_return_json,
)
from user_actions.tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")
TEST_TEXT = "Это отличный фильм! Очень рекомендую к просмотру."


class TestReviews:
    """Тесты эндпоинтов рецензий."""

    URL = f"{test_settings.api_prefix}/reviews/"

    async def test_create_review_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания рецензии."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": TEST_TEXT,
            "rating": 9,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None
        assert isinstance(data, dict)
        assert data["movie_id"] == str(movie_id)
        assert data["text"] == TEST_TEXT
        assert data["rating"] == 9

    async def test_get_my_reviews_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения моих рецензий."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
            "text": "Тестовая рецензия для проверки получения списка.",
            "rating": 8,
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

    async def test_get_movie_reviews_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения рецензий фильма."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для проверки получения рецензий фильма.",
            "rating": 7,
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

    async def test_delete_review_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления рецензии."""
        movie_id = uuid4()

        payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для последующего удаления.",
            "rating": 6,
        }
        await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.delete(
            f"{self.URL}{movie_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NO_CONTENT

    async def test_create_review_unauthorized(
        self,
        http_client: ClientSession,
    ):
        """Тест защиты эндпоинта: отсутствие токена авторизации."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия без авторизации.",
            "rating": 5,
        }

        response = await http_client.post(self.URL, json=payload)
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_create_review_validation_error(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест валидации: слишком короткий текст."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": "Коротко",  # меньше 10 символов
            "rating": 5,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY


class TestReviewLikes:
    """Тесты эндпоинтов лайков на рецензии."""

    LIKES_URL = f"{test_settings.api_prefix}/review-likes/"
    REVIEWS_URL = f"{test_settings.api_prefix}/reviews/"

    async def test_create_review_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания лайка на рецензию."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для тестирования лайков.",
            "rating": 8,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": True,
        }
        response = await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["review_id"] == str(review_id)
        assert data["is_like"] is True

    async def test_create_review_dislike_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест создания дизлайка на рецензию."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для тестирования дизлайков.",
            "rating": 7,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": False,
        }
        response = await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["review_id"] == str(review_id)
        assert data["is_like"] is False

    async def test_update_review_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест обновления лайка на рецензию (с like на dislike)."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для тестирования обновления лайка.",
            "rating": 9,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": True,
        }
        await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        dislike_payload = {
            "review_id": str(review_id),
            "is_like": False,
        }
        response = await http_client.post(
            self.LIKES_URL,
            json=dislike_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert data["is_like"] is False

    async def test_delete_review_like_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления лайка рецензии - лайк удален."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для тестирования удаления лайка.",
            "rating": 8,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": True,
        }
        await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.delete(
            f"{self.LIKES_URL}{review_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NO_CONTENT

    async def test_get_review_likes_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения лайков рецензии."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для проверки получения лайков.",
            "rating": 7,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": True,
        }
        await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.get(
            f"{self.LIKES_URL}review/{review_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_get_review_stats_success(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Позитивный тест получения статистики лайков рецензии."""
        movie_id = uuid4()
        review_payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для проверки статистики лайков.",
            "rating": 8,
        }
        review_response = await http_client.post(
            self.REVIEWS_URL,
            json=review_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        review_data = await assert_status_return_json(review_response, HTTPStatus.CREATED)
        assert review_data is not None and isinstance(review_data, dict)
        review_id = review_data["id"]

        like_payload = {
            "review_id": str(review_id),
            "is_like": True,
        }
        await http_client.post(
            self.LIKES_URL,
            json=like_payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )

        response = await http_client.get(
            f"{self.LIKES_URL}review/{review_id}/stats",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data is not None
        assert isinstance(data, dict)
        assert "likes" in data
        assert "dislikes" in data
        assert "total" in data
        assert "score" in data

    async def test_create_review_like_unauthorized(
        self,
        http_client: ClientSession,
    ):
        """Тест защиты эндпоинта: отсутствие токена авторизации."""
        like_payload = {
            "review_id": str(uuid4()),
            "is_like": True,
        }

        response = await http_client.post(self.LIKES_URL, json=like_payload)
        assert response.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_review_like_not_found(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Тест удаления несуществующего лайка рецензии."""
        review_id = uuid4()

        response = await http_client.delete(
            f"{self.LIKES_URL}{review_id}",
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        assert response.status == HTTPStatus.NOT_FOUND
