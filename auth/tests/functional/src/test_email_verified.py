"""Тесты поля email_verified: регистрация, ответ API, данные в БД."""

from http import HTTPStatus

import asyncpg
import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import assert_status_return_json

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestEmailVerifiedField:
    REGISTRATION_URL = f"{test_settings.api_prefix}/registration/"
    LOGIN_URL = f"{test_settings.api_prefix}/login/"

    async def test_registration_email_verified_is_false(
        self,
        http_client: ClientSession,
    ) -> None:
        """После регистрации email_verified=False в ответе."""
        response = await http_client.post(
            self.REGISTRATION_URL,
            json={
                "email": "email_verified_test@example.com",
                "password": "testpassword123",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data.get("email_verified") is False

    async def test_registration_email_verified_field_present(
        self,
        http_client: ClientSession,
    ) -> None:
        """Поле email_verified присутствует в ответе регистрации."""
        response = await http_client.post(
            self.REGISTRATION_URL,
            json={
                "email": "email_verified_field_test@example.com",
                "password": "testpassword123",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert "email_verified" in data

    async def test_registration_email_verified_false_in_db(
        self,
        http_client: ClientSession,
        pg_client: asyncpg.Connection,
    ) -> None:
        """После регистрации email_verified=False в БД."""
        test_email = "email_verified_db_test@example.com"
        response = await http_client.post(
            self.REGISTRATION_URL,
            json={
                "email": test_email,
                "password": "testpassword123",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        user_id = data["id"]

        row = await pg_client.fetchrow(
            "SELECT email_verified FROM users WHERE id = $1",
            user_id,
        )
        assert row is not None
        assert row["email_verified"] is False

    async def test_registration_by_phone_email_verified_false(
        self,
        http_client: ClientSession,
    ) -> None:
        """Регистрация по телефону: email_verified=False."""
        response = await http_client.post(
            self.REGISTRATION_URL,
            json={
                "phone": "+79123456789",
                "password": "testpassword123",
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data.get("email_verified") is False

    async def test_existing_user_email_verified_default_false(
        self,
        pg_client: asyncpg.Connection,
        active_user_data: dict,
    ) -> None:
        """Существующий пользователь (созданный фикстурой без email_verified)
        имеет email_verified=False после миграции (server_default=false)."""
        row = await pg_client.fetchrow(
            "SELECT email_verified FROM users WHERE id = $1",
            active_user_data["id"],
        )
        assert row is not None
        assert row["email_verified"] is False