from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings


class TestRegistration:
    URL = f"{test_settings.api_prefix}/registration/"
    
    @pytest.mark.asyncio
    async def test_registration_success(
        self,
        http_client: ClientSession,
    ):
        payload = {
            "email": "new_user@example.com",
            "password": "test_password",
        }

        response = await http_client.post(
            self.URL,
            json=payload,
        )

        assert response.status == HTTPStatus.CREATED

        data = await response.json()

        assert "id" in data
        assert data["email"] == payload["email"]
        assert data["is_staff"] is False
        assert data["is_active"] is True
        
    @pytest.mark.asyncio
    async def test_registration_user_already_exists(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        response = await http_client.post(
            self.URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )

        assert response.status == HTTPStatus.BAD_REQUEST

        data = await response.json()

        assert "detail" in data
        assert "error" in data["detail"]
    
    @pytest.mark.parametrize(
        'payload',
        [
            {"email": "12345678", "password": "12345678"},
            {"password": "12345678"},
            {"email": "only@email.com"},
        ]
    )    
    @pytest.mark.asyncio
    async def test_registration_user_with_invalid_data(
        self,
        http_client: ClientSession,
        payload: dict[str, str]
    ):
        response = await http_client.post(
            self.URL,
            json=payload,
        )

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY

        data = await response.json()

        assert "detail" in data


class TestLogin:
    URL = f"{test_settings.api_prefix}/login/"
    
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        response = await http_client.post(
            self.URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )

        assert response.status == HTTPStatus.OK

        data = await response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "access_token_expire" in data

        cookies = response.cookies

        assert "refresh_token" in cookies
        
    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.post(
            self.URL,
            json={
                "email": "unknown@example.com",
                "password": "password",
            },
        )

        assert response.status == HTTPStatus.NOT_FOUND

        data = await response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        
    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        response = await http_client.post(
            self.URL,
            json={
                "email": active_user_data["email"],
                "password": "wrong_password",
            },
        )

        assert response.status == HTTPStatus.UNAUTHORIZED

        data = await response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        
    @pytest.mark.parametrize(
        'payload',
        [
            {"email": "12345678", "password": "12345678"},
            {"password": "12345678"},
            {"email": "only@email.com"},
        ]
    )    
    @pytest.mark.asyncio
    async def test_login_user_with_invalid_data(
        self,
        http_client: ClientSession,
        payload: dict[str, str]
    ):
        response = await http_client.post(
            self.URL,
            json=payload,
        )

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY

        data = await response.json()

        assert "detail" in data


class TestPublicKey:
    URL = f"{test_settings.api_prefix}/jwt.key/"
    
    @pytest.mark.asyncio
    async def test_get_public_key(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.get(self.URL)

        assert response.status == HTTPStatus.OK

        data = await response.json()

        assert "public_key" in data
