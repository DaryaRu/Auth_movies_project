"""Помощник для работы с auth-сервисом в функциональных тестах.

Создаёт реальных пользователей через API auth-сервиса (регистрация + вход),
чтобы access-токены тестов были валидными и имели активные сессии —
user_actions проверяет сессии через auth-service.
"""

from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import aiohttp

from tests.settings import test_settings

TEST_PASSWORD = "TestPass123!"


def _auth_base() -> tuple[str, str]:
    """Возвращает (base_url, api_prefix) auth-сервиса из AUTH_API_URL."""
    parsed = urlsplit(test_settings.auth_api_url)
    return f"{parsed.scheme}://{parsed.netloc}", parsed.path.rstrip("/")


class AuthSession:
    """Результат регистрации и входа: идентификатор и токены пользователя."""

    def __init__(
        self, user_id: UUID, access_token: str, refresh_token: str | None
    ) -> None:
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token

    @property
    def headers(self) -> dict[str, str]:
        """Заголовки авторизации для запросов к user_actions."""
        return {"Authorization": f"Bearer {self.access_token}"}


async def _request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> aiohttp.ClientResponse:
    base_url, api_prefix = _auth_base()
    async with aiohttp.ClientSession(
        base_url=base_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4()), **(headers or {})},
    ) as session:
        response = await session.request(
            method, f"{api_prefix}{path}", json=json, cookies=cookies
        )
        await response.read()
        return response


async def register_and_login(
    *,
    password: str = TEST_PASSWORD,
    full_name: str | None = None,
) -> AuthSession:
    """Регистрирует нового пользователя и выполняет вход.

    Возвращает AuthSession с user_id, access-токеном (с активным sid)
    и refresh-токеном из cookie.
    """
    email = f"user-actions-test-{uuid4().hex}@example.com"

    reg_payload: dict[str, Any] = {"email": email, "password": password}
    if full_name:
        reg_payload["full_name"] = full_name
    reg_response = await _request("POST", "/registration/", json=reg_payload)
    assert reg_response.status == HTTPStatus.CREATED, (
        f"Регистрация не удалась: {reg_response.status} "
        f"{await reg_response.text()}"
    )
    user_data = await reg_response.json()

    login_response = await _request(
        "POST", "/login/", json={"email": email, "password": password}
    )
    assert login_response.status == HTTPStatus.OK, (
        f"Вход не удался: {login_response.status} "
        f"{await login_response.text()}"
    )
    login_data = await login_response.json()
    refresh_token_cookie = login_response.cookies.get("refresh_token")
    refresh_token = (
        refresh_token_cookie.value if refresh_token_cookie else None
    )

    return AuthSession(
        user_id=UUID(user_data["id"]),
        access_token=login_data["access_token"],
        refresh_token=refresh_token,
    )


async def logout(refresh_token: str) -> None:
    """Выход из аккаунта: отзыв текущей сессии (delete session by sid)."""
    assert refresh_token, "refresh-токен не получен при входе"
    response = await _request(
        "POST", "/logout/", cookies={"refresh_token": refresh_token}
    )
    assert response.status == HTTPStatus.NO_CONTENT, (
        f"Logout не удался: {response.status} {await response.text()}"
    )


async def delete_account(
    access_token: str, *, password: str = TEST_PASSWORD
) -> None:
    """Удаляет аккаунт пользователя (без телефона — подтверждение паролем).

    Auth-service синхронно очищает данные пользователя в user_actions,
    удаляет пользователя и отзывает все его сессии.
    """
    response = await _request(
        "POST",
        "/users/me/delete-account-request/",
        json={"password": password},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status == HTTPStatus.OK, (
        f"Удаление аккаунта не удалось: {response.status} "
        f"{await response.text()}"
    )
