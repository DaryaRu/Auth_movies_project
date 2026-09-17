"""Функциональные тесты смены email."""

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


async def _reset_email_change_state(
    redis_client: Redis, user_id: UUID, new_email: str | None = None
) -> None:
    """Точечно чистит ключи смены email для конкретного пользователя и адреса.

    email_change:{user_id} и email_change_attempts:{user_id} удаляются всегда.
    Кулдаун и лимит на старый адрес привязаны к user_id, на новый к new_email (если передан).
    """
    keys = [
        f"email_change:{user_id}",
        f"email_change_attempts:{user_id}",
        f"email_change_send_cooldown_old:{user_id}",
        f"email_change_send_rate_old:{user_id}",
    ]
    if new_email is not None:
        keys.append(f"email_change_send_cooldown_new:{new_email}")
        keys.append(f"email_change_send_rate_new:{new_email}")
    await redis_client.delete(*keys)


class TestRequestEmailChange:
    """Тесты POST /change-email-request/."""

    URL = f"{test_settings.api_prefix}/change-email-request/"

    async def test_request_email_change_wrong_password(
        self,
        http_client: ClientSession,
        email_change_user_token: str,
    ):
        """Отклоняет запрос смены email, если указан неверный текущий пароль, и возвращает 401."""
        response = await http_client.post(
            self.URL,
            json={
                "new_email": "wrong_password@example.com",
                "password": "wrong_password",
            },
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_request_email_change_already_taken(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        active_user_data: dict[str, Any],
    ):
        """Отклоняет запрос, если new_email уже занят другим аккаунтом, и возвращает 400."""
        response = await http_client.post(
            self.URL,
            json={
                "new_email": active_user_data["email"],
                "password": email_change_user_data["password"],
            },
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )
        assert_error_detail(data)

    async def test_request_email_change_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Отклоняет запрос смены email без токена авторизации и возвращает 401."""
        response = await http_client.post(
            self.URL,
            json={
                "new_email": "no_auth@example.com",
                "password": "any",
            },
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)


class TestVerifyOldEmail:
    """Тесты POST /verify-old-email/."""

    URL = f"{test_settings.api_prefix}/verify-old-email/"

    @staticmethod
    async def _seed_pending_old(
        redis_client: Redis, user_id: UUID, new_email: str, old_email_code: str
    ) -> None:
        """Записывает ожидающий запрос смены email напрямую
        в Redis, без реального запроса."""
        await redis_client.hset(  # type: ignore[misc]
            f"email_change:{user_id}",
            mapping={"new_email": new_email, "old_email_code": old_email_code},
        )

    async def test_verify_old_email_wrong_code(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Отклоняет неверный код со старого email и возвращает 401."""
        new_email = "verify_old_wrong@example.com"
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"], new_email
        )
        await self._seed_pending_old(
            redis_client, email_change_user_data["id"], new_email, "111111"
        )

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_verify_old_email_no_pending_request(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Отклоняет подтверждение, если не было предварительного запроса
        смены email (в Redis нет ожидающей записи), и возвращает 400."""
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"]
        )

        response = await http_client.post(
            self.URL,
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )
        assert_error_detail(data)

    async def test_verify_old_email_too_many_attempts(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Считает неверные попытки ввода кода: первые пять
        (EMAIL_CHANGE_MAX_ATTEMPTS=5) возвращают 401 каждая, а шестая
        превышает лимит попыток и возвращает 429."""
        new_email = "verify_old_attempts@example.com"
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"], new_email
        )
        await self._seed_pending_old(
            redis_client, email_change_user_data["id"], new_email, "222222"
        )

        for _ in range(5):
            response = await http_client.post(
                self.URL,
                json={"code": "000000"},
                headers={"Authorization": f"Bearer {email_change_user_token}"},
            )
            await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.TOO_MANY_REQUESTS
        )
        assert_error_detail(data)

    async def test_verify_old_email_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Отклоняет подтверждение кода старого email без токена авторизации и возвращает 401."""
        response = await http_client.post(
            self.URL,
            json={"code": "123456"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)


class TestVerifyNewEmail:
    """Тесты POST /verify-new-email/."""

    URL = f"{test_settings.api_prefix}/verify-new-email/"

    @staticmethod
    async def _seed_pending_new(
        redis_client: Redis, user_id: UUID, new_email: str, new_email_code: str
    ) -> None:
        """Записывает состояние "шаг 2 уже пройден" напрямую в Redis — код
        со старого адреса уже подтвержден, код на новый адрес сгенерирован.
        Изолирует тест verify-new-email от реальной доставки писем."""
        await redis_client.hset(  # type: ignore[misc]
            f"email_change:{user_id}",
            mapping={
                "new_email": new_email,
                "old_email_code": "000000",
                "new_email_code": new_email_code,
            },
        )

    async def test_verify_new_email_wrong_code(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Отклоняет неверный код с нового email и возвращает 401."""
        new_email = "verify_new_wrong@example.com"
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"], new_email
        )
        await self._seed_pending_new(
            redis_client, email_change_user_data["id"], new_email, "444444"
        )

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_verify_new_email_no_pending_request(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Отклоняет подтверждение нового email, если шаг 1 еще не
        завершен и в Redis нет new_email_code, и возвращает 400."""
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"]
        )

        response = await http_client.post(
            self.URL,
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )
        assert_error_detail(data)

    async def test_verify_new_email_too_many_attempts(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Считает неверные попытки ввода кода: первые пять
        (EMAIL_CHANGE_MAX_ATTEMPTS=5) возвращают 401 каждая, а шестая
        превышает лимит попыток и возвращает 429."""
        new_email = "verify_new_attempts@example.com"
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"], new_email
        )
        await self._seed_pending_new(
            redis_client, email_change_user_data["id"], new_email, "555555"
        )

        for _ in range(5):
            response = await http_client.post(
                self.URL,
                json={"code": "000000"},
                headers={"Authorization": f"Bearer {email_change_user_token}"},
            )
            await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)

        response = await http_client.post(
            self.URL,
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.TOO_MANY_REQUESTS
        )
        assert_error_detail(data)

    async def test_verify_new_email_without_auth(
        self,
        http_client: ClientSession,
    ):
        """Отклоняет подтверждение кода нового email без токена авторизации и возвращает 401."""
        response = await http_client.post(
            self.URL,
            json={"code": "123456"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_verify_new_email_success(
        self,
        http_client: ClientSession,
        email_change_user_data: dict[str, Any],
        email_change_user_token: str,
        redis_client: Redis,
    ):
        """Проверяет, что верный код нового email завершает смену: обновляет
        email пользователя в базе и помечает его подтвержденным
        (email_verified=True)."""
        new_email = "verify_new_success@example.com"
        await _reset_email_change_state(
            redis_client, email_change_user_data["id"], new_email
        )
        await self._seed_pending_new(
            redis_client, email_change_user_data["id"], new_email, "666666"
        )

        response = await http_client.post(
            self.URL,
            json={"code": "666666"},
            headers={"Authorization": f"Bearer {email_change_user_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["email"] == new_email
        assert data["email_verified"] is True
