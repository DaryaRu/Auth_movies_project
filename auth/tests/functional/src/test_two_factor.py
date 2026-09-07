"""Функциональные тесты 2FA-логина (POST /login/, POST /login/verify-phone/)."""

from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)
from redis.asyncio import Redis

pytestmark = pytest.mark.asyncio(loop_scope="session")

LOGIN_URL = f"{test_settings.api_prefix}/login/"
VERIFY_URL = f"{test_settings.api_prefix}/login/verify-phone/"


async def _seed_2fa_code(
    redis_client: Redis, user_id: UUID, code: str
) -> None:
    """Кладет код 2FA напрямую в Redis, без реальной отправки через SMSC."""
    await redis_client.setex(f"2fa_code:{user_id}", 300, code)


async def _reset_2fa_state(
    redis_client: Redis, phone_user_data: dict[str, Any]
) -> None:
    """Точечно чистит только ключи 2FA для конкретного пользователя/номера,
    в отличие от flush_redis_db."""
    user_id = phone_user_data["id"]
    phone = phone_user_data["phone"]
    await redis_client.delete(
        f"2fa_code:{user_id}",
        f"2fa_attempts:{user_id}",
        f"2fa_send_cooldown:{phone}",
        f"2fa_send_rate:{phone}",
    )


class TestLoginTriggersTwoFactor:
    """Определяет, включается ли второй шаг в зависимости от наличия телефона."""

    async def test_login_with_phone_returns_two_fa_required(
        self,
        http_client: ClientSession,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
        redis_client: Redis,
    ):
        """Единственный тест с реальной отправкой через SMSC (виртуальный режим)."""
        await _reset_2fa_state(redis_client, phone_user_data)

        response = await http_client.post(
            LOGIN_URL,
            json={
                "email": phone_user_data["email"],
                "password": phone_user_data["password"],
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data == {"two_fa_required": True}

    async def test_login_without_phone_stays_single_step(
        self,
        http_client: ClientSession,
        active_user_data: dict[str, Any],
    ):
        """Пользователь без телефона логинится в одно действие."""
        response = await http_client.post(
            LOGIN_URL,
            json={
                "email": active_user_data["email"],
                "password": active_user_data["password"],
            },
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "access_token" in data


class TestVerifyPhoneLogin:
    """Проверка кода. Код сидируется в Redis напрямую (независимо
    от того, реальная это отправка или нет)."""

    async def test_verify_phone_login_success(
        self,
        http_client: ClientSession,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
        redis_client: Redis,
    ):
        await _reset_2fa_state(redis_client, phone_user_data)
        await _seed_2fa_code(redis_client, phone_user_data["id"], "482913")

        response = await http_client.post(
            VERIFY_URL,
            json={"email": phone_user_data["email"], "code": "482913"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" in response.cookies

    async def test_verify_phone_login_wrong_code(
        self,
        http_client: ClientSession,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
        redis_client: Redis,
    ):
        await _reset_2fa_state(redis_client, phone_user_data)
        await _seed_2fa_code(redis_client, phone_user_data["id"], "482913")

        response = await http_client.post(
            VERIFY_URL,
            json={"email": phone_user_data["email"], "code": "000000"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_verify_phone_login_user_not_found(
        self,
        http_client: ClientSession,
    ):
        response = await http_client.post(
            VERIFY_URL,
            json={"email": "unknown-2fa@example.com", "code": "123456"},
        )
        data = await assert_status_return_json(response, HTTPStatus.NOT_FOUND)

        assert_error_detail(data)

    async def test_verify_phone_login_too_many_attempts(
        self,
        http_client: ClientSession,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
        redis_client: Redis,
    ):
        """TWO_FA_MAX_ATTEMPTS=5. Первые 5 неверных кодов выдают 401, шестой 429."""
        await _reset_2fa_state(redis_client, phone_user_data)
        await _seed_2fa_code(redis_client, phone_user_data["id"], "482913")

        for _ in range(5):
            response = await http_client.post(
                VERIFY_URL,
                json={"email": phone_user_data["email"], "code": "000000"},
            )
            await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        response = await http_client.post(
            VERIFY_URL,
            json={"email": phone_user_data["email"], "code": "000000"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.TOO_MANY_REQUESTS
        )

        assert_error_detail(data)
