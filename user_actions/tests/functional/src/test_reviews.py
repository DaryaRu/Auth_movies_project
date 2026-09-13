"""Функциональные тесты эндпоинтов рецензий и лайков на рецензии."""

from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import aiohttp
import pytest
from aiohttp import ClientSession

from tests.functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)
from tests.settings import test_settings

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


class TestReviewAuthorVisibility:
    """Тесты author_visibility в рецензиях."""

    URL = f"{test_settings.api_prefix}/reviews/"
    FULL_NAME = "Иванов Иван Иванович"
    NICKNAME = "movie_lover_42"

    async def _register_user(
        self,
        *,
        full_name: str | None = None,
    ) -> tuple[str, str]:
        """Зарегистрировать нового пользователя в auth-сервисе.

        Возвращает (email, password) созданного пользователя. Каждый вызов
        создаёт отдельного пользователя с уникальным email — тесты независимы.
        auth-сервис поднимается в тестовом окружении
        (см. tests/functional/docker-compose.yml).
        """
        email = f"review-author-{uuid4().hex[:10]}@example.com"
        password = "ReviewPass123!"

        parsed = urlsplit(test_settings.auth_api_url)
        session_base = f"{parsed.scheme}://{parsed.netloc}"
        api_prefix = parsed.path.rstrip("/")

        async with aiohttp.ClientSession(
            base_url=session_base,
            connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
            cookie_jar=aiohttp.DummyCookieJar(),
            timeout=aiohttp.ClientTimeout(total=None),
            headers={"X-Request-Id": str(uuid4())},
        ) as session:
            reg_payload: dict[str, Any] = {"email": email, "password": password}
            if full_name:
                reg_payload["full_name"] = full_name
            reg_response = await session.post(
                f"{api_prefix}/registration/", json=reg_payload
            )
            assert reg_response.status == HTTPStatus.CREATED, (
                f"Регистрация не удалась: {await reg_response.text()}"
            )

        return email, password

    async def _login_user(self, *, email: str, password: str) -> str:
        """Залогинить пользователя в auth-сервисе, вернуть JWT."""
        parsed = urlsplit(test_settings.auth_api_url)
        session_base = f"{parsed.scheme}://{parsed.netloc}"
        api_prefix = parsed.path.rstrip("/")

        async with aiohttp.ClientSession(
            base_url=session_base,
            connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
            cookie_jar=aiohttp.DummyCookieJar(),
            timeout=aiohttp.ClientTimeout(total=None),
            headers={"X-Request-Id": str(uuid4())},
        ) as session:
            login_response = await session.post(
                f"{api_prefix}/login/",
                json={"email": email, "password": password},
            )
            login_data = await assert_status_return_json(
                login_response, HTTPStatus.OK
            )
            assert login_data is not None
            return login_data["access_token"]

    async def _set_nickname(self, *, token: str, nickname: str) -> None:
        """Задать никнейм пользователю через profile-эндпоинт auth-сервиса.

        Никнейм нельзя задать на этапе регистрации, поэтому он выставляется
        отдельным запросом после логина.
        """
        parsed = urlsplit(test_settings.auth_api_url)
        session_base = f"{parsed.scheme}://{parsed.netloc}"
        api_prefix = parsed.path.rstrip("/")

        async with aiohttp.ClientSession(
            base_url=session_base,
            connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
            cookie_jar=aiohttp.DummyCookieJar(),
            timeout=aiohttp.ClientTimeout(total=None),
            headers={"X-Request-Id": str(uuid4())},
        ) as session:
            headers = {"Authorization": f"Bearer {token}"}
            nick_response = await session.patch(
                f"{api_prefix}/users/me/nickname/",
                json={"nickname": nickname},
                headers=headers,
            )
            assert nick_response.status == HTTPStatus.OK, (
                f"Не удалось задать никнейм: {await nick_response.text()}"
            )

    async def test_create_review_default_visibility_real_name(
        self,
        http_client: ClientSession,
    ):
        """По умолчанию author_visibility='real_name' и отображается ФИО автора.

        Регистрируется реальный пользователь с full_name, рецензия создаётся
        без явного author_visibility — должен примениться real_name.
        """
        email, password = await self._register_user(full_name=self.FULL_NAME)
        token = await self._login_user(email=email, password=password)
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": TEST_TEXT,
            "rating": 8,
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)

        assert data is not None
        assert isinstance(data, dict)
        assert data["movie_id"] == str(movie_id)
        assert data["rating"] == 8
        assert data["author_visibility"] == "real_name"
        assert data["author_name"] == self.FULL_NAME

    async def test_create_review_with_anonymous_visibility(
        self,
        http_client: ClientSession,
    ):
        """Создание рецензии с author_visibility='anonymous' — имя скрыто «Аноним».

        Регистрируется реальный пользователь с full_name, ему задаётся никнейм,
        затем создаётся рецензия с author_visibility='anonymous'. Несмотря на
        установленные ФИО и никнейм, в ответе отображается «Аноним» — ни полное
        имя, ни никнейм не должны попасть в author_name.
        """
        email, password = await self._register_user(full_name=self.FULL_NAME)
        token = await self._login_user(email=email, password=password)
        await self._set_nickname(token=token, nickname=self.NICKNAME)
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": TEST_TEXT,
            "rating": 7,
            "author_visibility": "anonymous",
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)

        assert data is not None
        assert data["author_visibility"] == "anonymous"
        assert data["author_name"] == "Аноним"
        assert data["author_name"] != self.NICKNAME
        assert data["author_name"] != self.FULL_NAME

    async def test_create_review_with_real_name_visibility(
        self,
        http_client: ClientSession,
    ):
        """Создание рецензии с author_visibility='real_name' — отображается ФИО автора.

        Регистрируется реальный пользователь с full_name в auth-БД, и user_actions
        сохраняет snapshot ФИО при создании рецензии.
        """
        email, password = await self._register_user(full_name=self.FULL_NAME)
        token = await self._login_user(email=email, password=password)
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": "Полноценная рецензия с отображением автора.",
            "rating": 10,
            "author_visibility": "real_name",
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)

        assert data is not None
        assert data["author_visibility"] == "real_name"
        assert isinstance(data["author_name"], str)
        assert data["author_name"] == self.FULL_NAME

    async def test_create_review_with_nickname_visibility(
        self,
        http_client: ClientSession,
    ):
        """Создание рецензии с author_visibility='nickname' — отображается никнейм.

        Регистрируется реальный пользователь, ему задаётся никнейм в профиле,
        и user_actions сохраняет snapshot никнейма при создании рецензии.
        """
        email, password = await self._register_user()
        token = await self._login_user(email=email, password=password)
        await self._set_nickname(token=token, nickname=self.NICKNAME)
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия с никнеймом автора.",
            "rating": 8,
            "author_visibility": "nickname",
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)

        assert data is not None
        assert data["author_visibility"] == "nickname"
        assert isinstance(data["author_name"], str)
        assert data["author_name"] == self.NICKNAME

    async def test_create_review_invalid_author_visibility(
        self,
        http_client: ClientSession,
        generate_test_token: str,
    ):
        """Невалидное значение author_visibility — 422."""
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": TEST_TEXT,
            "rating": 5,
            "author_visibility": "secret_name",
        }

        response = await http_client.post(
            self.URL,
            json=payload,
            headers={"Authorization": f"Bearer {generate_test_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNPROCESSABLE_ENTITY
        )
        assert_error_detail(data)

    async def test_get_movie_reviews_include_author_name(
        self,
        http_client: ClientSession,
    ):
        """Получение рецензий фильма с проверкой author_name и author_visibility.

        Регистрируется реальный пользователь, создаётся рецензия с
        author_visibility='anonymous'. Рецензия должна отображаться в списке
        рецензий фильма с author_name='Аноним'.
        """
        email, password = await self._register_user(full_name=self.FULL_NAME)
        token = await self._login_user(email=email, password=password)
        movie_id = uuid4()
        payload = {
            "movie_id": str(movie_id),
            "text": "Рецензия для проверки author_name в списке.",
            "rating": 9,
            "author_visibility": "anonymous",
        }
        created = await assert_status_return_json(
            await http_client.post(
                self.URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            ),
            HTTPStatus.CREATED,
        )

        response = await http_client.get(
            f"{self.URL}movie/{movie_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data
        assert data["total"] >= 1
        # В списке должна присутствовать именно созданная рецензия (ищем по id),
        # а не произвольный элемент.
        item = next(
            (i for i in data["items"] if i["id"] == created["id"]),
            None,
        )
        assert item is not None, "Созданная рецензия не найдена в списке рецензий фильма"
        assert item["movie_id"] == str(movie_id)
        assert "author_name" in item
        assert "author_visibility" in item
        assert item["author_visibility"] == "anonymous"
        assert item["author_name"] == "Аноним"
