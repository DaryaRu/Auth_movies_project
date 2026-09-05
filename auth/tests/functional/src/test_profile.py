"""Функциональные тесты профиля пользователя."""

from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _login(http_client: ClientSession, email: str, password: str) -> str:
    response = await http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={"email": email, "password": password},
    )
    data = await assert_status_return_json(response, HTTPStatus.OK)
    return data["access_token"]


class TestGetProfile:
    URL = f"{test_settings.api_prefix}/users/me/"

    async def test_get_profile_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        token = await _login(
            http_client,
            active_user_data["email"],
            active_user_data["password"],
        )
        response = await http_client.get(
            self.URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["email"] == active_user_data["email"]
        assert data["is_active"] is True
        assert "id" in data
        assert "phone" in data
        assert "full_name" in data
        assert "timezone" in data
        assert "email_verified" in data

    async def test_get_profile_without_auth(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.get(self.URL)
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)


class TestUpdateFullName:
    URL = f"{test_settings.api_prefix}/users/me/full-name/"

    async def test_update_full_name_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        token = await _login(
            http_client,
            active_user_data["email"],
            active_user_data["password"],
        )
        response = await http_client.patch(
            self.URL,
            json={"full_name": "Иванов Иван Иванович"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["full_name"] == "Иванов Иван Иванович"

    @pytest.mark.parametrize(
        "full_name",
        [
            "Ян",
            "123",
            "Иван_Иванов",
        ],
    )
    async def test_update_full_name_invalid(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
        full_name: str,
    ):
        token = await _login(
            http_client,
            active_user_data["email"],
            active_user_data["password"],
        )
        response = await http_client.patch(
            self.URL,
            json={"full_name": full_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNPROCESSABLE_ENTITY
        )

        assert "detail" in data

    async def test_update_full_name_without_auth(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.patch(
            self.URL,
            json={"full_name": "Иванов Иван Иванович"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)
