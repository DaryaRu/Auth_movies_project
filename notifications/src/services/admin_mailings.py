"""Сервис для ручных рассылок из админки (Scheduled group / Immediate group)."""

import json
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiokafka.errors import KafkaError

from src.clients.auth import search_distinct_timezones
from src.core.config import settings
from src.db import kafka
from src.repositories.admin_mailings import AdminMailingRepository
from src.repositories.templates import TemplateRepository
from src.schemas.admin_mailings import AdminMailing
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)

logger = logging.getLogger(__name__)


class InvalidScheduledAtError(Exception):
    """scheduled_at указан неверно (задавать в будущем)."""


def _next_local_time_as_utc(local_time: str, tz_name: str) -> datetime | None:
    """Момент, когда в таймзоне tz_name наступит local_time (HH:MM), в UTC."""
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning(
            f"Неизвестная таймзона {tz_name}: рассылка для пользователей "
            f"этой таймзоны не будет создана"
        )
        return None
    hour, minute = (int(part) for part in local_time.split(":"))
    now_local = datetime.now(tz)
    candidate = datetime.combine(
        now_local.date(), time(hour, minute), tzinfo=tz
    )
    if candidate <= now_local:
        candidate = datetime.combine(
            now_local.date() + timedelta(days=1), time(hour, minute), tzinfo=tz
        )
    return candidate.astimezone(timezone.utc)


class AdminMailingService:
    """Сервис для создания ручных рассылок."""

    def __init__(
        self,
        mailing_repository: AdminMailingRepository,
        template_repository: TemplateRepository,
    ):
        self.mailing_repo = mailing_repository
        self.template_repo = template_repository

    async def create(
        self,
        template_id: UUID,
        audience_filter: dict[str, Any],
        payload: dict[str, Any],
        scheduled_at: datetime | None,
        scheduled_local_time: str | None,
        created_by: UUID,
    ) -> list[AdminMailing]:
        """Создать рассылку.

        Если ни scheduled_at, ни scheduled_local_time не заданы, отправка происходит
        сразу (Immediate group): публикуется в notification-pending, потом с известным
        admin_mailing_id создается запись в БД со status=sending. Если Kafka недоступна,
        публикация падает раньше записи в БД и не будет ошибочной строки со статусом
        sending без реального отправленного сообщения.

        scheduled_at задавать в будущем, status=scheduled — одна рассылка.

        scheduled_local_time (HH:MM) разбивает аудиторию по её таймзонам и создаёт
        по одной рассылке status=scheduled на каждую таймзону, с scheduled_at,
        рассчитанным как ближайшее будущее наступление local_time в этой таймзоне.
        """
        template = await self.template_repo.get_by_id(template_id)
        if template is None or not template.is_active:
            raise TemplateNotFoundError(str(template_id))

        if template.allowed_variables:
            unknown_keys = set(payload.keys()) - set(
                template.allowed_variables
            )
            if unknown_keys:
                raise InvalidPayloadError(unknown_keys)

        if scheduled_at is not None and scheduled_at <= datetime.now(
            timezone.utc
        ):
            raise InvalidScheduledAtError(str(scheduled_at))

        if scheduled_local_time is not None:
            return await self._create_bucketed_by_timezone(
                template_id,
                audience_filter,
                payload,
                scheduled_local_time,
                created_by,
            )

        status = "scheduled" if scheduled_at is not None else "sending"
        admin_mailing_id = uuid4()

        if status == "sending":
            await self._publish_pending(
                admin_mailing_id, template_id, audience_filter, payload
            )

        mailing = await self.mailing_repo.create(
            admin_mailing_id,
            template_id,
            audience_filter,
            payload,
            status,
            scheduled_at,
            created_by,
        )
        return [mailing]

    async def _create_bucketed_by_timezone(
        self,
        template_id: UUID,
        audience_filter: dict[str, Any],
        payload: dict[str, Any],
        scheduled_local_time: str,
        created_by: UUID,
    ) -> list[AdminMailing]:
        """Разбить рассылку на несколько физических рассылок, по одной на каждую
        таймзону, встречающуюся у аудитории, подходящей под audience_filter."""
        timezones = await search_distinct_timezones(audience_filter)
        mailings = []
        for tz_name in timezones:
            scheduled_at = _next_local_time_as_utc(
                scheduled_local_time, tz_name
            )
            if scheduled_at is None:
                continue
            bucket_filter = {**audience_filter, "timezone": tz_name}
            mailing = await self.mailing_repo.create(
                uuid4(),
                template_id,
                bucket_filter,
                payload,
                "scheduled",
                scheduled_at,
                created_by,
            )
            mailings.append(mailing)
        return mailings

    async def _publish_pending(
        self,
        admin_mailing_id: UUID,
        template_id: UUID,
        audience_filter: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Опубликовать неполное сообщение в notification-pending. А резолв
        аудитории по audience_filter и реальную отправку делает воркер."""
        message = {
            "admin_mailing_id": str(admin_mailing_id),
            "template_id": str(template_id),
            "audience_filter": audience_filter,
            "payload": payload,
        }
        assert kafka.producer is not None
        try:
            await kafka.producer.send_and_wait(
                settings.KAFKA_PENDING_TOPIC,
                value=json.dumps(message).encode(),
                key=str(admin_mailing_id).encode(),
            )
        except KafkaError as e:
            raise RuntimeError(
                f"Failed to publish admin mailing to Kafka: {e}"
            ) from e
