"""Тесты для batch endpoint получения имён пользователей."""

from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from tests.functional.settings import test_settings
from tests.functional.utils.check_methods import (
    assert_status_return_json,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestGetUsersNamesBatch:
    """Тесты для POST /api/v1/internal/users/names."""

    URL = f"{test_settings.api_prefix}/internal/users/names"

    async def test_get_users_names_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Успешный запрос пакетного получения имён."""
        response = await http_client.post(
            self.URL,
            json={"user_ids": [str(active_user_data["id"])]},
            headers={
                "X-Internal-Secret": test_settings.internal_service_secret,
                "Content-Type": "application/json",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        user_snapshot = data[str(active_user_data["id"])]
        assert user_snapshot == {
            "full_name": None,
            "nickname": None,
        }

    async def test_get_users_names_empty_list(
        self,
        http_client: ClientSession,
    ):
        """Пустой список user_ids — 422."""
        response = await http_client.post(
            self.URL,
            json={"user_ids": []},
            headers={
                "X-Internal-Secret": test_settings.internal_service_secret,
                "Content-Type": "application/json",
            },
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNPROCESSABLE_ENTITY
        )
        assert "detail" in data

    async def test_get_users_names_without_secret(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Запрос без X-Internal-Secret — 401."""
        response = await http_client.post(
            self.URL,
            json={"user_ids": [str(active_user_data["id"])]},
            headers={"Content-Type": "application/json"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert data == {"detail": "Invalid internal secret"}

    async def test_get_users_names_invalid_secret(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Запрос с невалидным X-Internal-Secret — 401."""
        response = await http_client.post(
            self.URL,
            json={"user_ids": [str(active_user_data["id"])]},
            headers={
                "X-Internal-Secret": "wrong_secret",
                "Content-Type": "application/json",
            },
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert data == {"detail": "Invalid internal secret"}

    async def test_get_users_names_nonexistent_users(
        self,
        http_client: ClientSession,
    ):
        """Запрос для несуществующих пользователей — 200 с пустым результатом.

        Репозиторий возвращает строки только для существующих пользователей,
        поэтому несуществующие UUID не попадают в ответ (200 OK, пустой dict).
        """
        fake_ids = [str(uuid4()), str(uuid4())]
        response = await http_client.post(
            self.URL,
            json={"user_ids": fake_ids},
            headers={
                "X-Internal-Secret": test_settings.internal_service_secret,
                "Content-Type": "application/json",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        for fake_id in fake_ids:
            assert fake_id not in data
