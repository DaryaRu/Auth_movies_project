"""Функциональные тесты эндпоинтов настроек уведомлений пользователя."""

import asyncio
import uuid
from http import HTTPStatus

import asyncpg
import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Дефолтные настройки уведомлений
DEFAULT_NOTIFICATIONS_ENABLED = True
DEFAULT_EMAIL_ENABLED = True
DEFAULT_SMS_ENABLED = False
DEFAULT_PUSH_ENABLED = True

NOTIFICATION_SETTINGS_URL = (
    f"{test_settings.api_prefix}/users/me/notification-settings/"
)
REGISTRATION_URL = f"{test_settings.api_prefix}/registration/"
LOGIN_URL = f"{test_settings.api_prefix}/login/"


class TestNotificationSettingsWithoutAuth:
    """Тесты проверки 401 при отсутствии токена."""

    async def test_get_notification_settings_without_auth_returns_401(
        self,
        http_client: ClientSession,
    ) -> None:
        """Запрос GET настроек уведомлений без токена возвращает 401."""
        response = await http_client.get(NOTIFICATION_SETTINGS_URL)
        data = await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)
        assert_error_detail(data)

    async def test_patch_notification_settings_without_auth_returns_401(
        self,
        http_client: ClientSession,
    ) -> None:
        """Запрос PATCH настроек уведомлений без токена возвращает 401."""
        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL, json={"email_enabled": False}
        )
        await assert_status_return_json(response, HTTPStatus.UNAUTHORIZED)


class TestGetNotificationSettings:
    """Тесты GET /users/me/notification-settings/."""

    async def test_get_notification_settings_returns_defaults(
        self, http_client: ClientSession, active_user_data: dict
    ) -> None:
        """Первый запрос GET возвращает дефолтные значения."""
        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": active_user_data["email"], "password": active_user_data["password"]},
        )
        access_token = (await login_resp.json())["access_token"]
        response = await http_client.get(
            NOTIFICATION_SETTINGS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["user_id"] == str(active_user_data["id"])
        assert data["notifications_enabled"] == DEFAULT_NOTIFICATIONS_ENABLED
        assert data["email_enabled"] == DEFAULT_EMAIL_ENABLED
        assert data["sms_enabled"] == DEFAULT_SMS_ENABLED
        assert data["push_enabled"] == DEFAULT_PUSH_ENABLED

    async def test_get_notification_settings_does_not_create_record_in_db(
        self,
        http_client: ClientSession,
        active_user_data: dict,
        pg_client: asyncpg.Connection,
    ) -> None:
        """GET не создаёт запись в БД — это read-only операция."""
        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": active_user_data["email"], "password": active_user_data["password"]},
        )
        access_token = (await login_resp.json())["access_token"]
        await http_client.get(
            NOTIFICATION_SETTINGS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        row = await pg_client.fetchrow(
            "SELECT user_id FROM user_notification_settings WHERE user_id = $1",
            active_user_data["id"],
        )
        assert row is None

    async def test_get_notification_settings_idempotent(
        self, http_client: ClientSession, active_user_data: dict
    ) -> None:
        """Повторный GET возвращает те же данные."""
        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": active_user_data["email"], "password": active_user_data["password"]},
        )
        access_token = (await login_resp.json())["access_token"]
        data1 = await (
            await http_client.get(
                NOTIFICATION_SETTINGS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        ).json()
        data2 = await (
            await http_client.get(
                NOTIFICATION_SETTINGS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        ).json()
        assert data1 == data2


class TestPatchNotificationSettings:
    """Тесты PATCH /users/me/notification-settings/."""

    async def test_patch_updates_existing_settings(
        self, http_client: ClientSession, active_user_data: dict
    ) -> None:
        """PATCH обновляет существующие настройки."""
        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": active_user_data["email"], "password": active_user_data["password"]},
        )
        access_token = (await login_resp.json())["access_token"]

        # Сначала создаём запись через GET
        await http_client.get(
            NOTIFICATION_SETTINGS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # PATCH обновляет только email и sms
        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"email_enabled": False, "sms_enabled": True},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["email_enabled"] is False
        assert data["sms_enabled"] is True
        # Остальные поля не изменились
        assert data["notifications_enabled"] is True
        assert data["push_enabled"] is True

    async def test_patch_updates_all_fields(
        self, http_client: ClientSession, active_user_data: dict
    ) -> None:
        """PATCH может обновить все поля одновременно."""
        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": active_user_data["email"], "password": active_user_data["password"]},
        )
        access_token = (await login_resp.json())["access_token"]

        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={
                "notifications_enabled": False,
                "email_enabled": False,
                "sms_enabled": False,
                "push_enabled": False,
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["notifications_enabled"] is False
        assert data["email_enabled"] is False
        assert data["sms_enabled"] is False
        assert data["push_enabled"] is False

    async def test_patch_creates_record_if_not_exists(
        self, http_client: ClientSession, pg_client: asyncpg.Connection
    ) -> None:
        """PATCH создаёт запись, если её ещё нет."""
        test_email = f"patch_create_{uuid.uuid4().hex[:8]}@example.com"
        reg_response = await http_client.post(
            REGISTRATION_URL,
            json={"email": test_email, "password": "testpassword123"},
        )
        await assert_status_return_json(reg_response, HTTPStatus.CREATED)

        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": test_email, "password": "testpassword123"},
        )
        access_token = (await login_resp.json())["access_token"]

        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"email_enabled": False, "push_enabled": False},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["email_enabled"] is False
        assert data["push_enabled"] is False
        assert data["notifications_enabled"] is True
        assert data["sms_enabled"] is False

        await asyncio.sleep(0.1) #запись в базу
        row = await pg_client.fetchrow(
            "SELECT notifications_enabled, email_enabled, sms_enabled, push_enabled "
            "FROM user_notification_settings WHERE user_id = $1",
            uuid.UUID(data["user_id"]) if isinstance(data["user_id"], str) else data["user_id"],
        )
        assert row is not None
        assert row["email_enabled"] is False
        assert row["push_enabled"] is False
        assert row["notifications_enabled"] is True
        assert row["sms_enabled"] is False


    async def test_patch_partial_update_preserves_other_fields(
        self, http_client: ClientSession
    ) -> None:
        """PATCH с одним полем не меняет остальные поля.
        Если записи не существовало, отсутствующие значения заполнены дефолтами."""
        test_email = f"patch_partial_{uuid.uuid4().hex[:8]}@example.com"
        await assert_status_return_json(
            await http_client.post(REGISTRATION_URL, json={"email": test_email, "password": "testpassword123"}),
            HTTPStatus.CREATED
        )

        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": test_email, "password": "testpassword123"},
        )
        access_token = (await login_resp.json())["access_token"]

        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"email_enabled": False},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["email_enabled"] is False
        
        # Остальные поля должны инициализироваться дефолтами
        assert data["notifications_enabled"] == DEFAULT_NOTIFICATIONS_ENABLED
        assert data["sms_enabled"] == DEFAULT_SMS_ENABLED
        assert data["push_enabled"] == DEFAULT_PUSH_ENABLED

    async def test_patch_with_invalid_types_returns_422(
        self, http_client: ClientSession
    ) -> None:
        """Передача некорректных типов данных в PATCH возвращает ошибку валидации 422."""
        test_email = f"patch_invalid_{uuid.uuid4().hex[:8]}@example.com"
        await assert_status_return_json(
            await http_client.post(REGISTRATION_URL, json={"email": test_email, "password": "testpassword123"}),
            HTTPStatus.CREATED
        )

        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": test_email, "password": "testpassword123"},
        )
        access_token = (await login_resp.json())["access_token"]

        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={"email_enabled": "not-a-boolean-value"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        await assert_status_return_json(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_patch_empty_body_returns_ok_and_preserves_data(
        self, http_client: ClientSession
    ) -> None:
        """Передача пустого body в PATCH не приводит к ошибке бэкенда."""
        test_email = f"patch_empty_{uuid.uuid4().hex[:8]}@example.com"
        await assert_status_return_json(
            await http_client.post(REGISTRATION_URL, json={"email": test_email, "password": "testpassword123"}),
            HTTPStatus.CREATED
        )

        login_resp = await http_client.post(
            LOGIN_URL,
            json={"email": test_email, "password": "testpassword123"},
        )
        access_token = (await login_resp.json())["access_token"]

        response = await http_client.patch(
            NOTIFICATION_SETTINGS_URL,
            json={},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["notifications_enabled"] == DEFAULT_NOTIFICATIONS_ENABLED
