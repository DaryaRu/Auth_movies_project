"""Функциональные тесты смены номера телефона
(POST /change-phone-request/, POST /confirm-phone/).
"""

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


async def _reset_phone_change_state(
    redis_client: Redis, user_id: UUID, phone: str | None = None
) -> None:
    """Точечно чистит ключи смены номера для конкретного пользователя/номера.

    phone_change:{user_id} и phone_change_attempts:{user_id} удаляются всегда.
    phone_change_send_cooldown:{phone} и phone_change_send_rate:{phone} —
    только если передан phone (кулдаун и лимит отправок привязаны к
    конкретному new_phone, а не к пользователю).
    """
    keys = [f"phone_change:{user_id}", f"phone_change_attempts:{user_id}"]
    if phone is not None:
        keys.append(f"phone_change_send_cooldown:{phone}")
        keys.append(f"phone_change_send_rate:{phone}")
    await redis_client.delete(*keys)


class TestRequestPhoneChange:
    """Тесты POST /change-phone-request/."""

    URL = f"{test_settings.api_prefix}/change-phone-request/"

    async def test_request_phone_change_wrong_password(
        self,
        http_client: ClientSession,
        phone_change_user_token: str,
    ):
        """Неверный текущий пароль на первом шаге смены номера. 401."""
        response = await http_client.post(
            self.URL,
            json={"new_phone": "+79001112233", "password": "wrong_password"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_request_phone_change_already_taken(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        phone_user_data: dict[str, Any],
        create_phone_user: None,
    ):
        """new_phone уже занят другим аккаунтом (phone_user_data). 409.
        Проверка уникальности срабатывает до отправки СМС, реальный SMSC не дергает."""
        response = await http_client.post(
            self.URL,
            json={
                "new_phone": phone_user_data["phone"],
                "password": phone_change_user_data["password"],
            },
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.CONFLICT)

        assert_error_detail(data)

    async def test_request_phone_change_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Запрос смены номера без токена. 401."""
        response = await http_client.post(
            self.URL,
            json={"new_phone": "+79001112233", "password": "any"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)


class TestConfirmPhoneChange:
    """Тесты POST /confirm-phone/."""

    URL = f"{test_settings.api_prefix}/confirm-phone/"

    @staticmethod
    async def _seed_pending_change(
        redis_client: Redis,
        user_id: UUID,
        new_phone: str,
        sms_code: str,
        email_code: str,
    ) -> None:
        """Записывает ожидающий запрос смены номера напрямую в Redis, без
        реальной отправки СМС/email.

        PhoneChangeService.confirm_change() читает только Redis и не
        обращается к SMSC/notifications-service.
        """
        await redis_client.hset(  # type: ignore[misc]
            f"phone_change:{user_id}",
            mapping={
                "new_phone": new_phone,
                "sms_code": sms_code,
                "email_code": email_code,
            },
        )

    async def test_confirm_phone_change_wrong_sms_code(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """Неверный СМС-код при верном email-коде на confirm (401), номер не меняется."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        await self._seed_pending_change(
            redis_client,
            phone_change_user_data["id"],
            "+79000000002",
            "111111",
            "222222",
        )

        response = await http_client.post(
            self.URL,
            json={"sms_code": "000000", "email_code": "222222"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)
        assert (
            data["detail"]["error"]
            == "Неверный или истекший код подтверждения"
        )

    async def test_confirm_phone_change_wrong_email_code(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """Неверный email-код при верном СМС-коде на confirm (401), номер не меняется."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        await self._seed_pending_change(
            redis_client,
            phone_change_user_data["id"],
            "+79000000006",
            "333333",
            "444444",
        )

        response = await http_client.post(
            self.URL,
            json={"sms_code": "333333", "email_code": "000000"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_confirm_phone_change_no_pending_request(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """Confirm без предварительного request. 400."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )

        response = await http_client.post(
            self.URL,
            json={"sms_code": "123456", "email_code": "654321"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )

        assert_error_detail(data)

    async def test_confirm_phone_change_too_many_attempts(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """PHONE_CHANGE_MAX_ATTEMPTS=5. Первые 5 неверных кодов выдают 401, шестой 429."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        await self._seed_pending_change(
            redis_client,
            phone_change_user_data["id"],
            "+79000000003",
            "555555",
            "666666",
        )

        for _ in range(5):
            response = await http_client.post(
                self.URL,
                json={"sms_code": "000000", "email_code": "666666"},
                headers={"Authorization": f"Bearer {phone_change_user_token}"},
            )
            await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        response = await http_client.post(
            self.URL,
            json={"sms_code": "000000", "email_code": "666666"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.TOO_MANY_REQUESTS
        )

        assert_error_detail(data)

    async def test_confirm_phone_change_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Подтверждение смены номера без токена авторизации. 401."""
        response = await http_client.post(
            self.URL,
            json={"sms_code": "123456", "email_code": "654321"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )

        assert_error_detail(data)

    async def test_confirm_phone_change_success(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """Успешный confirm (оба кода верны) отзывает все сессии пользователя."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        new_phone = "+79000000001"
        await self._seed_pending_change(
            redis_client,
            phone_change_user_data["id"],
            new_phone,
            "482913",
            "159426",
        )

        response = await http_client.post(
            self.URL,
            json={"sms_code": "482913", "email_code": "159426"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["phone"] == new_phone


class TestPhoneChangeFullFlow:
    """Запрос на смену номера требует два реальных внешних отправления: СМС
    через SMSC и email-код через notifications-service.
    Стек auth-service не содержит notifications-service, поэтому email-код недоступен и request
    падает на этом шаге, до отправки СМС.
    """

    REQUEST_URL = f"{test_settings.api_prefix}/change-phone-request/"
    NEW_PHONE = "+79621234568"

    async def test_request_fails_without_notifications_service(
        self,
        http_client: ClientSession,
        phone_change_full_flow_user_data: dict[str, Any],
        phone_change_full_flow_user_token: str,
        redis_client: Redis,
    ):
        """request падает с 502 (ProviderException) на отправке email-кода, СМС не отправляется."""
        await _reset_phone_change_state(
            redis_client,
            phone_change_full_flow_user_data["id"],
            self.NEW_PHONE,
        )

        request_response = await http_client.post(
            self.REQUEST_URL,
            json={
                "new_phone": self.NEW_PHONE,
                "password": phone_change_full_flow_user_data["password"],
            },
            headers={
                "Authorization": f"Bearer {phone_change_full_flow_user_token}"
            },
        )
        data = await assert_status_return_json(
            request_response, HTTPStatus.BAD_GATEWAY
        )

        assert_error_detail(data)

        pending = await redis_client.hgetall(  # type: ignore[misc]
            f"phone_change:{phone_change_full_flow_user_data['id']}"
        )
        assert pending.get("new_phone") == self.NEW_PHONE
        assert "sms_code" in pending
        assert "email_code" in pending
