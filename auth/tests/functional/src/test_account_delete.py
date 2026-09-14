"""Функциональные тесты удаления аккаунта
(POST /users/me/delete-account-request/, POST /users/me/delete-account-confirm/).

Тестовый стек auth-service не поднимает user-actions-service,
поэтому реальное удаление аккаунта не происходит. После исчерпания
ретраев проверяется, что ответ 503 (AccountDeleteUnavailableException)."""

import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)
from functional.utils.helpers import hash_password
from redis.asyncio import Redis

pytestmark = pytest.mark.asyncio(loop_scope="session")

REQUEST_URL = f"{test_settings.api_prefix}/users/me/delete-account-request/"
CONFIRM_URL = f"{test_settings.api_prefix}/users/me/delete-account-confirm/"
LOGIN_URL = f"{test_settings.api_prefix}/login/"
VERIFY_URL = f"{test_settings.api_prefix}/login/verify-phone/"

PASSWORD = "deleteaccount12345"


async def _create_user(
    pg_write_data, *, phone: str | None = None
) -> dict[str, Any]:
    """Создает отдельного пользователя для теста удаления, не переиспользуя общие session-scoped фикстуры."""
    data = {
        "id": uuid.uuid4(),
        "email": f"delete_{uuid.uuid4().hex[:8]}@example.com",
        "hashed_password": hash_password(PASSWORD),
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if phone:
        data["phone"] = phone
    await pg_write_data("users", tuple(data.keys()), tuple(data.values()))
    return data


async def _login(
    http_client: ClientSession, email: str, password: str
) -> dict[str, Any]:
    """Логинится по email+паролю и возвращает тело ответа (access_token или two_fa_required)."""
    response = await http_client.post(
        LOGIN_URL, json={"email": email, "password": password}
    )
    return await response.json()


async def _seed_2fa_code(
    redis_client: Redis, user_id: uuid.UUID, code: str
) -> None:
    """Кладет код 2FA напрямую в Redis, без реальной отправки через SMSC."""
    await redis_client.setex(f"2fa_code:{user_id}", 300, code)


async def _reset_2fa_state(
    redis_client: Redis, user_id: uuid.UUID, phone: str
) -> None:
    """Точечно чистит ключи 2FA для конкретного пользователя и номера."""
    await redis_client.delete(
        f"2fa_code:{user_id}",
        f"2fa_attempts:{user_id}",
        f"2fa_send_cooldown:{phone}",
        f"2fa_send_rate:{phone}",
    )


class TestRequestAccountDelete:
    """Тесты POST /users/me/delete-account-request/."""

    async def test_request_without_phone_correct_password(
        self, http_client: ClientSession, pg_write_data
    ):
        """Телефона нет, пароль верный — идет до удаления сразу (без кода подтверждения);
        получает 503 из-за недоступности user-actions-service."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)

        response = await http_client.post(
            REQUEST_URL,
            json={"password": PASSWORD},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.SERVICE_UNAVAILABLE
        )
        assert_error_detail(data)

    async def test_request_without_phone_wrong_password(
        self, http_client: ClientSession, pg_write_data
    ):
        """Проверяет пароль, находит несовпадение и отвечает 401."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)

        response = await http_client.post(
            REQUEST_URL,
            json={"password": "wrong-password"},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_request_without_phone_missing_password(
        self, http_client: ClientSession, pg_write_data
    ):
        """Если нет пароля в теле запроса, то получает 401 (как при неверном пароле)."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)

        response = await http_client.post(
            REQUEST_URL,
            json={},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_request_with_phone_sends_sms_and_does_not_delete(
        self,
        http_client: ClientSession,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
        redis_client: Redis,
    ):
        """Пользователь с телефоном делает запрос на удаление аккаунта:
        request_account_delete отправляет реальный СМС-код через SMSC (виртуальный режим) и отвечает
        200 {"two_fa_required": true}. Другие тесты идут по ветке без телефона (сразу к удалению)
        и поэтому получают 503, а не 200."""
        user_id = phone_user_data["id"]
        phone = phone_user_data["phone"]
        await _reset_2fa_state(redis_client, user_id, phone)
        await _seed_2fa_code(redis_client, user_id, "482913")
        verify_response = await http_client.post(
            VERIFY_URL,
            json={"email": phone_user_data["email"], "code": "482913"},
        )
        verify_data = await assert_status_return_json(
            verify_response, HTTPStatus.OK
        )
        token = verify_data["access_token"]

        try:
            response = await http_client.post(
                REQUEST_URL,
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
            data = await assert_status_return_json(response, HTTPStatus.OK)
            assert data["two_fa_required"] is True
        finally:
            await _reset_2fa_state(redis_client, user_id, phone)

    async def test_request_without_auth(self, http_client: ClientSession):
        """Отправляет запрос без токена авторизации и получает 401."""
        response = await http_client.post(
            REQUEST_URL, json={"password": PASSWORD}
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)


class TestConfirmAccountDelete:
    """Тесты POST /users/me/delete-account-confirm/."""

    async def test_confirm_with_correct_code(
        self,
        http_client: ClientSession,
        pg_write_data,
        redis_client: Redis,
    ):
        """Код верный, поэтому идем до удаления и получаем 503 из-за недоступности user-actions-service."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)
        code = "482913"
        await _seed_2fa_code(redis_client, user["id"], code)

        response = await http_client.post(
            CONFIRM_URL,
            json={"code": code},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.SERVICE_UNAVAILABLE
        )
        assert_error_detail(data)

    async def test_confirm_with_wrong_code(
        self,
        http_client: ClientSession,
        pg_write_data,
        redis_client: Redis,
    ):
        """Проверяет код, находит несовпадение и отвечает 401."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)
        await _seed_2fa_code(redis_client, user["id"], "111111")

        response = await http_client.post(
            CONFIRM_URL,
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_confirm_without_requested_code(
        self, http_client: ClientSession, pg_write_data
    ):
        """Пытается подтвердить код, которого нет в Redis, получает 401."""
        user = await _create_user(pg_write_data)
        login_data = await _login(http_client, user["email"], PASSWORD)

        response = await http_client.post(
            CONFIRM_URL,
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_confirm_without_auth(self, http_client: ClientSession):
        """Отправляет запрос без токена авторизации и получает 401."""
        response = await http_client.post(CONFIRM_URL, json={"code": "123456"})
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)
