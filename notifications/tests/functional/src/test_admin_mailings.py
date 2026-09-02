"""Тесты для admin_mailings."""

import asyncio
import json
from datetime import datetime
from http import HTTPStatus
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from aiohttp import ClientSession
from settings import test_settings
from utils.check_methods import assert_status, assert_status_return_json

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEMPLATES_URL = f"{test_settings.api_v1_prefix}/notifications/templates/"
MAILINGS_URL = f"{test_settings.api_v1_prefix}/admin-mailings/"

USUAL_TIMEZONE = "Europe/Moscow"
ONE_MORE_TIMEZONE = "America/New_York"
TIMEZONE_FOR_CHANGE = "Europe/Kaliningrad"
USUAL_TIMEZONE_1 = "Europe/London"


async def _consume_until(
    consumer, predicate: Callable[[dict], bool], timeout: float
) -> dict:
    """Топик общий на все тесты в прогоне, читает сообщения по порядку, пока
    не найдет нужное (по predicate)."""

    async def _loop() -> dict:
        async for msg in consumer:
            data = json.loads(msg.value)
            if predicate(data):
                return data
        raise RuntimeError("consumer closed before a matching message arrived")

    return await asyncio.wait_for(_loop(), timeout=timeout)


async def _register_user(
    auth_client: ClientSession,
    *,
    email: str,
    password: str = "TestPass123!",
    timezone: str | None = None,
) -> dict:
    payload = {"email": email, "password": password}
    if timezone is not None:
        payload["timezone"] = timezone
    response = await auth_client.post(
        f"{test_settings.auth_api_url}/registration/", json=payload
    )
    return await assert_status_return_json(response, HTTPStatus.CREATED)


async def _create_template(http_client: ClientSession) -> dict:
    payload: dict[str, Any] = {
        "code": f"functest_{uuid4().hex[:12]}",
        "name": "Functional test template",
        "channel": "email",
        "subject": None,
        "body": "Тестовое письмо.",
        "allowed_variables": [],
        "is_active": True,
    }
    response = await http_client.post(TEMPLATES_URL, json=payload)
    return await assert_status_return_json(response, HTTPStatus.CREATED)


async def _change_user_timezone(
    auth_client: ClientSession, user_email: str, new_timezone: str
) -> dict:
    """Смена таймзоны пользователя."""
    # Сначала логинимся как пользователь для получения токена
    login_response = await auth_client.post(
        f"{test_settings.auth_api_url}/login/",
        json={"email": user_email, "password": "TestPass123!"},
    )
    login_data = await assert_status_return_json(login_response, HTTPStatus.OK)
    token = login_data["access_token"]

    # Меняем таймзону
    response = await auth_client.patch(
        f"{test_settings.auth_api_url}/users/me/timezone/",
        json={"timezone": new_timezone},
        headers={"Authorization": f"Bearer {token}"},
    )
    return await assert_status_return_json(response, HTTPStatus.OK)


def _create_mailing_payload(template_id: str, **overrides) -> dict:
    payload = {
        "template_id": template_id,
        "audience_filter": {},
        "payload": {},
        "created_by": str(uuid4()),
    }
    payload.update(overrides)
    return payload


class TestAdminMailingImmediate:
    """Рассылка без scheduled_local_datetime, отправка сразу (Immediate group)."""

    async def test_publishes_to_notification_pending(
        self, http_client: ClientSession, kafka_consumer_factory
    ):
        """Создание рассылки публикует сообщение в notification-pending с теми
        же template_id/audience_filter/payload, что были в запросе."""
        consumer = await kafka_consumer_factory(
            test_settings.kafka_pending_topic
        )
        template = await _create_template(http_client)

        response = await http_client.post(
            MAILINGS_URL, json=_create_mailing_payload(template["template_id"])
        )
        mailings = await assert_status_return_json(
            response, HTTPStatus.CREATED
        )
        assert len(mailings) == 1
        mailing = mailings[0]
        assert mailing["status"] == "sending"
        assert mailing["scheduled_at"] is None

        data = await _consume_until(
            consumer,
            lambda d: d.get("admin_mailing_id") == mailing["admin_mailing_id"],
            test_settings.kafka_consumer_timeout_sec,
        )
        assert data["template_id"] == template["template_id"]
        assert data["audience_filter"] == {}
        assert data["payload"] == {}

    async def test_unknown_template_returns_404(
        self, http_client: ClientSession
    ):
        """Несуществующий template_id. 404, рассылка не создается."""
        response = await http_client.post(
            MAILINGS_URL, json=_create_mailing_payload(str(uuid4()))
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_invalid_payload_key_returns_422(
        self, http_client: ClientSession
    ):
        """Payload содержит ключ, не входящий в allowed_variables шаблона. 422."""
        template = await _create_template(http_client)
        response = await http_client.post(
            MAILINGS_URL,
            json=_create_mailing_payload(
                template["template_id"], payload={"unexpected": "x"}
            ),
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestAdminMailingGet:
    """GET /admin-mailings/ и /admin-mailings/{id}/."""

    async def test_get_by_id(self, http_client: ClientSession):
        """Созданная рассылка находится по своему admin_mailing_id."""
        template = await _create_template(http_client)
        create_response = await http_client.post(
            MAILINGS_URL, json=_create_mailing_payload(template["template_id"])
        )
        created = (await create_response.json())[0]

        response = await http_client.get(
            f"{MAILINGS_URL}{created['admin_mailing_id']}/"
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["admin_mailing_id"] == created["admin_mailing_id"]

    async def test_get_by_id_not_found(self, http_client: ClientSession):
        """Несуществующий admin_mailing_id. 404."""
        response = await http_client.get(f"{MAILINGS_URL}{uuid4()}/")
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_list_includes_created(self, http_client: ClientSession):
        """Список рассылок включает только что созданную."""
        template = await _create_template(http_client)
        create_response = await http_client.post(
            MAILINGS_URL, json=_create_mailing_payload(template["template_id"])
        )
        created = (await create_response.json())[0]

        response = await http_client.get(MAILINGS_URL)
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert any(
            m["admin_mailing_id"] == created["admin_mailing_id"] for m in data
        )


class TestAdminMailingTimezoneBucketing:
    """Рассылка со scheduled_local_datetime, разбивка аудитории по таймзонам."""

    async def test_creates_one_bucket_per_timezone_with_correct_utc(
        self, http_client: ClientSession, auth_client: ClientSession
    ):
        """Регистрирует юзеров с разными таймзонами (без нее трактуется как UTC)."""
        suffix = uuid4().hex[:8]
        await _register_user(
            auth_client,
            email=f"tz-moscow-{suffix}@example.com",
            timezone=USUAL_TIMEZONE,
        )
        await _register_user(
            auth_client,
            email=f"tz-newyork-{suffix}@example.com",
            timezone=ONE_MORE_TIMEZONE ,
        )
        await _register_user(
            auth_client, email=f"tz-none-{suffix}@example.com"
        )
        template = await _create_template(http_client)
        local_datetime = "2099-06-15T09:30:00"

        response = await http_client.post(
            MAILINGS_URL,
            json=_create_mailing_payload(
                template["template_id"],
                scheduled_local_datetime=local_datetime,
            ),
        )
        mailings = await assert_status_return_json(
            response, HTTPStatus.CREATED
        )

        buckets = {m["audience_filter"]["timezone"]: m for m in mailings}
        assert {USUAL_TIMEZONE, ONE_MORE_TIMEZONE , "UTC"} <= set(buckets)

        naive = datetime.fromisoformat(local_datetime)
        for tz_name in (USUAL_TIMEZONE, ONE_MORE_TIMEZONE, "UTC"):
            bucket = buckets[tz_name]
            assert bucket["status"] == "scheduled"
            expected_utc = naive.replace(tzinfo=ZoneInfo(tz_name)).astimezone(
                ZoneInfo("UTC")
            )
            actual_utc = datetime.fromisoformat(
                bucket["scheduled_at"].replace("Z", "+00:00")
            )
            assert actual_utc == expected_utc

    async def test_past_local_datetime_returns_no_buckets(
        self, http_client: ClientSession, auth_client: ClientSession
    ):
        """Если указанный местный момент уже прошел для всех таймзон
        аудитории, рассылка не создается."""
        suffix = uuid4().hex[:8]
        await _register_user(
            auth_client,
            email=f"tz-past-{suffix}@example.com",
            timezone=USUAL_TIMEZONE,
        )
        template = await _create_template(http_client)

        response = await http_client.post(
            MAILINGS_URL,
            json=_create_mailing_payload(
                template["template_id"],
                scheduled_local_datetime="2020-01-01T00:00:00",
            ),
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data == []

    async def test_timezone_change_affects_new_mailing(
        self, http_client: ClientSession, auth_client: ClientSession
    ):
        """Если изменить таймзону у пользователя, новая рассылка учитывает это изменение."""
        suffix = uuid4().hex[:8]
        
        user = await _register_user(
            auth_client,
            email=f"tz-moscow2-{suffix}@example.com",
            timezone=USUAL_TIMEZONE_1,
        )

        await _change_user_timezone(
            auth_client, user["email"], TIMEZONE_FOR_CHANGE
        )

        template = await _create_template(http_client)
        local_datetime = "2099-06-15T09:30:00"

        response = await http_client.post(
            MAILINGS_URL,
            json=_create_mailing_payload(
                template["template_id"],
                scheduled_local_datetime=local_datetime,
            ),
        )
        mailings = await assert_status_return_json(response, HTTPStatus.CREATED)
        
        created_timezones = {m["audience_filter"]["timezone"] for m in mailings}
    
        # Проверяем, что создалась рассылка для новой таймзоны
        # Для старой - не создалась
        assert TIMEZONE_FOR_CHANGE in created_timezones, ("Рассылка для пользователя "
                                                         "после смены таймзоны не создана!")
        assert USUAL_TIMEZONE_1 not in created_timezones, ("Ошибка! Создалась рассылка "
                                                           "для старой таймзоны пользователя")
