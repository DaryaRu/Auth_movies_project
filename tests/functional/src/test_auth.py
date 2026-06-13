"""Функциональные тесты эндпоинтов аутентификации."""

from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status,
    assert_status_return_json,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestRegistration:
    URL = f"{test_settings.api_prefix}/registration/"

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
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert "id" in data
        assert data["email"] == payload["email"]
        assert data["is_superuser"] is False
        assert data["is_active"] is True

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
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )

        assert_error_detail(data)

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "12345678", "password": "12345678"},
            {"password": "12345678"},
            {"email": "only@email.com"},
        ],
    )
    async def test_registration_user_with_invalid_data(
        self, http_client: ClientSession, payload: dict[str, str]
    ):
        response = await http_client.post(
            self.URL,
            json=payload,
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNPROCESSABLE_ENTITY
        )

        assert "detail" in data


class TestLogin:
    URL = f"{test_settings.api_prefix}/login/"

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
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "access_token_expire" in data

        cookies = response.cookies

        assert "refresh_token" in cookies

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
        data = await assert_status_return_json(response, HTTPStatus.NOT_FOUND)

        assert_error_detail(data)

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
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "12345678", "password": "12345678"},
            {"password": "12345678"},
            {"email": "only@email.com"},
        ],
    )
    async def test_login_user_with_invalid_data(
        self, http_client: ClientSession, payload: dict[str, str]
    ):
        response = await http_client.post(
            self.URL,
            json=payload,
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNPROCESSABLE_ENTITY
        )

        assert "detail" in data


class TestPublicKey:
    URL = f"{test_settings.api_prefix}/jwt.key/"

    async def test_get_public_key(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.get(self.URL)
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "public_key" in data


class TestRefreshToken:
    URL = f"{test_settings.api_prefix}/refresh/"
    LOGIN_URL = f"{test_settings.api_prefix}/login/"

    async def test_refresh_token_success(
        self,
        cookie_http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Успешное обновление токена возвращает 200 с новым access_token и refresh_token в cookie."""
        login_response = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        assert login_response.status == HTTPStatus.OK, (
            f"Login failed: {await login_response.text()}"
        )
        await login_response.json()  # потребляем тело ответа, чтобы куки попали в jar

        response = await cookie_http_client.post(self.URL)
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "access_token_expire" in data
        assert "refresh_token" in response.cookies

    async def test_refresh_token_without_cookie(
        self,
        http_client: ClientSession,
    ):
        """Запрос обновления токена без cookie возвращает 401."""
        response = await http_client.post(self.URL)
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_refresh_token_invalid_token(
        self,
        http_client: ClientSession,
    ):
        """Запрос обновления токена с невалидным значением cookie возвращает 401."""
        response = await http_client.post(
            self.URL,
            headers={"Cookie": "refresh_token=invalid.token.value"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)


class TestLogout:
    URL = f"{test_settings.api_prefix}/logout/"
    LOGIN_URL = f"{test_settings.api_prefix}/login/"
    REFRESH_URL = f"{test_settings.api_prefix}/refresh/"

    async def test_logout_success(
        self,
        cookie_http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Успешный выход возвращает 204 и удаляет refresh_token из БД."""
        login_response = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        await login_response.json()  # потребляем тело ответа, чтобы куки попали в jar

        response = await cookie_http_client.post(self.URL)
        await assert_status(response, HTTPStatus.NO_CONTENT)

    async def test_logout_without_token(
        self,
        http_client: ClientSession,
    ):
        """Запрос выхода без cookie возвращает 401."""
        response = await http_client.post(self.URL)
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_refresh_fails_after_logout(
        self,
        cookie_http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """После выхода попытка обновить токен возвращает 401 (токен удалён из БД)."""
        login_response = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        await login_response.json()  # потребляем тело ответа, чтобы куки попали в jar

        await cookie_http_client.post(self.URL)

        response = await cookie_http_client.post(self.REFRESH_URL)
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)
        
        
class TestLogoutAll:
    LOGOUT_ALL_URL = f"{test_settings.api_prefix}/logout-all/"
    LOGIN_URL = f"{test_settings.api_prefix}/login/"
    ACTIVE_SESSION_URL = f"{test_settings.api_prefix}/active_sessions/"
    
    async def test_logout_all_success(
        self,
        cookie_http_client: ClientSession,
        active_user_data: dict[str, Any],
    ) -> None:
        """Успешный выход возвращает 204 и удаляет refresh_token из БД."""
        login_response_1 = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                )
            }
        )
        login_response_2 = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.3 Mobile/15E148 Safari/604.1"
                )
            }
        )
        login_data_1 = await login_response_1.json()
        access_token_1 = login_data_1["access_token"]

        login_data_2 = await login_response_2.json()
        access_token_2 = login_data_2["access_token"]

        response = await cookie_http_client.post(self.LOGOUT_ALL_URL)
        await assert_status(response, HTTPStatus.NO_CONTENT)
        
        session_response_1 = await cookie_http_client.get(
            self.ACTIVE_SESSION_URL,
            headers = {"Authorization": f"Bearer {access_token_1}"}
        )
        await assert_status(session_response_1, HTTPStatus.UNAUTHORIZED)
        session_response_2 = await cookie_http_client.get(
            self.ACTIVE_SESSION_URL,
            headers = {"Authorization": f"Bearer {access_token_2}"}
        )
        await assert_status(session_response_2, HTTPStatus.UNAUTHORIZED)
        
    async def test_logout_all_without_token(
        self,
        http_client: ClientSession,
    ) -> None:
        """Запрос выхода без cookie возвращает 401."""
        response = await http_client.post(self.LOGOUT_ALL_URL)
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)
        

class TestActiveSession:
    LOGIN_URL = f"{test_settings.api_prefix}/login/"
    ACTIVE_SESSION_URL = f"{test_settings.api_prefix}/active_sessions/"
    LOGOUT_URL = f"{test_settings.api_prefix}/logout/"
    
    async def test_get_active_session_success(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
        flush_redis_db: None,
    ) -> None:
        login_response = await http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        login_data = await login_response.json()
        access_token = login_data["access_token"]
        active_session_response = await http_client.get(
            self.ACTIVE_SESSION_URL,
            headers = {"Authorization": f"Bearer {access_token}"}
        )
        data = await assert_status_return_json(active_session_response, HTTPStatus.OK)
        assert len(data) == 1
        assert "user_agent" in data[0]
        assert "ip" in data[0]
        assert "created_at" in data[0]
        assert "is_current" in data[0]
        
    async def test_change_in_active_sessions(
        self,
        cookie_http_client: ClientSession,
        active_user_data: dict[str, Any],
        flush_redis_db: None,
    ) -> None:
        login_response_1 = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0.0.0 Safari/537.36"
                )
            }
        )
        login_response_2 = await cookie_http_client.post(
            self.LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.3 Mobile/15E148 Safari/604.1"
                )
            }
        )
        login_data_1 = await login_response_1.json()
        access_token_1 = login_data_1["access_token"]

        login_data_2 = await login_response_2.json()
        access_token_2 = login_data_2["access_token"]
        active_session_response = await cookie_http_client.get(
            self.ACTIVE_SESSION_URL,
            headers = {"Authorization": f"Bearer {access_token_2}"}
        )
        data = await assert_status_return_json(active_session_response, HTTPStatus.OK)
        assert len(data) == 2
        assert sum(item["is_current"] for item in data) == 1
        logout_response = await cookie_http_client.post(self.LOGOUT_URL)
        await assert_status(logout_response, HTTPStatus.NO_CONTENT)
        active_session_response = await cookie_http_client.get(
            self.ACTIVE_SESSION_URL,
            headers = {"Authorization": f"Bearer {access_token_1}"}
        )
        data = await assert_status_return_json(active_session_response, HTTPStatus.OK)
        assert len(data) == 1

    async def test_get_active_session_error_without_headers(
        self,
        http_client: ClientSession,
    ) -> None:
        response = await http_client.get(
            self.ACTIVE_SESSION_URL,
        )
        data = await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)
        assert_error_detail(data)
