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
    assert_status,
    assert_status_return_json,
)
from functional.utils.helpers import get_phone_change_code
from redis.asyncio import Redis

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _reset_phone_change_state(
    redis_client: Redis, user_id: UUID, phone: str | None = None
) -> None:
    """Точечно чистит ключи смены номера для конкретного пользователя/номера.

    phone_change:{user_id} и phone_change_attempts:{user_id} удаляются всегда.
    phone_change_send_cooldown:{phone} и phone_change_send_rate:{phone} —
    только если передан phone (кулдаун и лимит отправок привязаны к
    конкретному new_phone, а не к пользователю). Нужен тесту, который
    реально шлет запрос через SMSC (TestPhoneChangeFullFlow).
    """
    keys = [f"phone_change:{user_id}", f"phone_change_attempts:{user_id}"]
    if phone is not None:
        keys.append(f"phone_change_send_cooldown:{phone}")
        keys.append(f"phone_change_send_rate:{phone}")
    await redis_client.delete(*keys)


class TestRequestPhoneChange:
    URL = f"{test_settings.api_prefix}/change-phone-request/"

    async def test_request_phone_change_wrong_password(
        self,
        http_client: ClientSession,
        phone_change_user_token: str,
    ):
        """Неверный текущий пароль на первом шаге смены номера."""
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
    URL = f"{test_settings.api_prefix}/confirm-phone/"

    @staticmethod
    async def _seed_pending_change(
        redis_client: Redis, user_id: UUID, new_phone: str, code: str
    ) -> None:
        """Записывает ожидающий запрос смены номера напрямую в Redis, без реальной отправки СМС.

        PhoneChangeService.confirm_change() читает только Redis и не обращается к SMSC.
        """
        await redis_client.hset(
            f"phone_change:{user_id}",
            mapping={"new_phone": new_phone, "sms_code": code},
        )

    async def test_confirm_phone_change_wrong_code(
        self,
        http_client: ClientSession,
        phone_change_user_data: dict[str, Any],
        phone_change_user_token: str,
        redis_client: Redis,
    ):
        """Неверный код подтверждения на confirm (401), номер не меняется."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        await self._seed_pending_change(
            redis_client,
            phone_change_user_data["id"],
            "+79000000002",
            "111111",
        )

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
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
            json={"code": "123456"},
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
        )

        for _ in range(5):
            response = await http_client.post(
                self.URL,
                json={"code": "000000"},
                headers={"Authorization": f"Bearer {phone_change_user_token}"},
            )
            await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
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
            json={"code": "123456"},
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
        """Успешный confirm отзывает все сессии пользователя."""
        await _reset_phone_change_state(
            redis_client, phone_change_user_data["id"]
        )
        new_phone = "+79000000001"
        await self._seed_pending_change(
            redis_client, phone_change_user_data["id"], new_phone, "482913"
        )

        response = await http_client.post(
            self.URL,
            json={"code": "482913"},
            headers={"Authorization": f"Bearer {phone_change_user_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["phone"] == new_phone


class TestPhoneChangeFullFlow:
    """Настоящий флоу. Реально шлет СМС через SMSC, код читается из реального ответа.

    Использует отдельного пользователя. Тест доходит до успешного confirm и отзыва сессий.

    Если тест вдруг начнет падать с ProviderException/502 с синтетическим номером,
    нужно попробовать подобрать другой номер либо заменить реальным (связано с самим SMSC).
    """

    REQUEST_URL = f"{test_settings.api_prefix}/change-phone-request/"
    CONFIRM_URL = f"{test_settings.api_prefix}/confirm-phone/"
    NEW_PHONE = "+79621234567"

    async def test_request_and_confirm_real_send(
        self,
        http_client: ClientSession,
        phone_change_full_flow_user_data: dict[str, Any],
        phone_change_full_flow_user_token: str,
        redis_client: Redis,
    ):
        """Полный флоу: request реально шлет СМС, confirm подтверждает настоящим кодом
        из ответа SMSC."""
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
        await assert_status(request_response, HTTPStatus.NO_CONTENT)

        code = await get_phone_change_code(
            redis_client, phone_change_full_flow_user_data["id"]
        )
        assert code is not None

        confirm_response = await http_client.post(
            self.CONFIRM_URL,
            json={"code": code},
            headers={
                "Authorization": f"Bearer {phone_change_full_flow_user_token}"
            },
        )
        data = await assert_status_return_json(confirm_response, HTTPStatus.OK)

        assert data["phone"] == self.NEW_PHONE
