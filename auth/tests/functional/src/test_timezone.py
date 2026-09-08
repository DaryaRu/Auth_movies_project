# -*- coding: utf-8 -*-
"""Функциональные тесты эндпоинта смены таймзоны."""

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


class TestChangeTimezone:
    URL = f"{test_settings.api_prefix}/users/me/timezone/"

    async def test_change_timezone_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Успешная смена таймзоны."""
        login_response = await http_client.post(
            f"{test_settings.api_prefix}/login/",
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        login_data = await assert_status_return_json(login_response, HTTPStatus.OK)
        access_token = login_data["access_token"]

        new_timezone = "America/New_York"
        response = await http_client.patch(
            self.URL,
            json={"timezone": new_timezone},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["timezone"] == new_timezone
        assert "id" in data
        assert "email" in data

    async def test_change_timezone_invalid(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Попытка сменить на некорректную таймзону."""
        login_response = await http_client.post(
            f"{test_settings.api_prefix}/login/",
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        login_data = await assert_status_return_json(login_response, HTTPStatus.OK)
        access_token = login_data["access_token"]

        response = await http_client.patch(
            self.URL,
            json={"timezone": "Invalid/Timezone"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.UNPROCESSABLE_ENTITY)

        assert "detail" in data
        assert "timezone" in str(data["detail"])

    async def test_change_timezone_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Попытка сменить таймзону без токена."""
        response = await http_client.patch(
            self.URL,
            json={"timezone": "Europe/Moscow"},
        )
        data = await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        assert_error_detail(data)
