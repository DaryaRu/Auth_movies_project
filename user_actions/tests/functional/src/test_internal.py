"""Функциональные тесты internal-эндпоинта удаления данных пользователя
(DELETE /internal/users/{user_id}/actions/)."""

from http import HTTPStatus
from uuid import uuid4

import asyncpg
import pytest
from aiohttp import ClientSession

from tests.functional.utils.auth_api import register_and_login
from tests.functional.utils.check_methods import (
    assert_status,
    assert_status_return_json,
)
from tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")

INTERNAL_URL = "/api/v1/internal"
TEST_TEXT = "Рецензия для теста."


class TestDeleteUserActions:
    """Тесты DELETE /internal/users/{user_id}/actions/."""

    async def test_delete_user_actions_requires_secret(
        self, http_client: ClientSession
    ):
        """Отправляет запрос без заголовка X-Internal-Secret и получает 401."""
        response = await http_client.delete(
            f"{INTERNAL_URL}/users/{uuid4()}/actions/"
        )
        await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_delete_user_actions_wrong_secret(
        self, http_client: ClientSession
    ):
        """Передает неверный X-Internal-Secret и получает 401."""
        response = await http_client.delete(
            f"{INTERNAL_URL}/users/{uuid4()}/actions/",
            headers={"X-Internal-Secret": "wrong-secret"},
        )
        await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_delete_user_actions_removes_all_data(
        self,
        http_client: ClientSession,
        pg_client: asyncpg.Connection,
    ):
        """Удаляет закладки, оценки, рецензии и лайки рецензий пользователя
        (включая лайки на чужие рецензии), не трогая данные других
        пользователей. Лайки других пользователей на удаленные рецензии этого
        пользователя удаляются каскадно."""
        deleted_user = await register_and_login()
        other_user = await register_and_login()
        deleted_user_id = deleted_user.user_id
        other_user_id = other_user.user_id
        deleted_user_headers = deleted_user.headers
        other_user_headers = other_user.headers

        movie_id = uuid4()
        other_movie_id = uuid4()

        await http_client.post(
            "/api/v1/user-actions/bookmarks/",
            json={"movie_id": str(movie_id)},
            headers=deleted_user_headers,
        )
        await http_client.post(
            "/api/v1/user-actions/likes/",
            json={"movie_id": str(movie_id), "rating": 10},
            headers=deleted_user_headers,
        )
        deleted_user_review_resp = await http_client.post(
            "/api/v1/user-actions/reviews/",
            json={"movie_id": str(movie_id), "text": TEST_TEXT, "rating": 8},
            headers=deleted_user_headers,
        )
        deleted_user_review = await assert_status_return_json(
            deleted_user_review_resp, HTTPStatus.CREATED
        )
        deleted_user_review_id = deleted_user_review["id"]

        other_user_review_resp = await http_client.post(
            "/api/v1/user-actions/reviews/",
            json={
                "movie_id": str(other_movie_id),
                "text": TEST_TEXT,
                "rating": 7,
            },
            headers=other_user_headers,
        )
        other_user_review = await assert_status_return_json(
            other_user_review_resp, HTTPStatus.CREATED
        )
        other_user_review_id = other_user_review["id"]

        await http_client.post(
            "/api/v1/user-actions/review-likes/",
            json={"review_id": other_user_review_id, "is_like": True},
            headers=deleted_user_headers,
        )
        await http_client.post(
            "/api/v1/user-actions/review-likes/",
            json={"review_id": deleted_user_review_id, "is_like": True},
            headers=other_user_headers,
        )

        response = await http_client.delete(
            f"{INTERNAL_URL}/users/{deleted_user_id}/actions/",
            headers={
                "X-Internal-Secret": test_settings.internal_service_secret
            },
        )
        await assert_status(response, HTTPStatus.NO_CONTENT)

        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM bookmarks WHERE user_id = $1",
                deleted_user_id,
            )
            == 0
        )
        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM likes WHERE user_id = $1",
                deleted_user_id,
            )
            == 0
        )
        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM reviews WHERE user_id = $1",
                deleted_user_id,
            )
            == 0
        )
        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM review_likes WHERE user_id = $1",
                deleted_user_id,
            )
            == 0
        )

        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM review_likes WHERE review_id = $1",
                deleted_user_review_id,
            )
            == 0
        )

        assert (
            await pg_client.fetchval(
                "SELECT COUNT(*) FROM reviews WHERE user_id = $1",
                other_user_id,
            )
            == 1
        )

    async def test_delete_user_actions_idempotent(
        self, http_client: ClientSession
    ):
        """Для проверки идемпотентности вызывает удаление два раза подряд для одного и того же user_id,
        и оба раза получает 204."""
        user_id = uuid4()
        headers = {"X-Internal-Secret": test_settings.internal_service_secret}

        first = await http_client.delete(
            f"{INTERNAL_URL}/users/{user_id}/actions/", headers=headers
        )
        await assert_status(first, HTTPStatus.NO_CONTENT)

        second = await http_client.delete(
            f"{INTERNAL_URL}/users/{user_id}/actions/", headers=headers
        )
        await assert_status(second, HTTPStatus.NO_CONTENT)
