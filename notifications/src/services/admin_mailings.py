"""Сервис для ручных рассылок из админки (Scheduled group / Immediate group)."""

import json
import logging
from datetime import datetime, timezone
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


def _local_datetime_to_utc(
    local_datetime: datetime, tz_name: str
) -> datetime | None:
    """local_datetime в таймзоне tz_name, переведенный в UTC.
    None, если tz_name невалидна или если этот
    момент уже в прошлом — такая таймзона просто пропускается."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        logger.warning(
            f"Неизвестная таймзона {tz_name}: рассылка для пользователей "
            f"этой таймзоны не будет создана"
        )
        return None

    scheduled_at = local_datetime.replace(tzinfo=tz).astimezone(timezone.utc)
    if scheduled_at <= datetime.now(timezone.utc):
        logger.warning(
            f"Для таймзоны {tz_name} указанное местное время уже прошло: "
            f"рассылка для неё не будет создана"
        )
        return None
    return scheduled_at


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
        scheduled_local_datetime: datetime | None,
        created_by: UUID,
    ) -> list[AdminMailing]:
        """Создать рассылку.

        Если scheduled_local_datetime не задан, отправка происходит сразу
        (Immediate group): публикуется в notification-pending, потом с
        известным admin_mailing_id создается запись в БД со status=sending.
        Если Kafka недоступна, публикация падает раньше записи в БД и не
        будет ошибочной строки со статусом sending без реального
        отправленного сообщения.
        """
        template = await self.template_repo.get_by_id(template_id)
        if template is None or not template.is_active:
            raise TemplateNotFoundError(str(template_id))

        unknown_keys = set(payload.keys()) - set(template.allowed_variables)
        if unknown_keys:
            raise InvalidPayloadError(unknown_keys)

        if scheduled_local_datetime is not None:
            return await self._create_bucketed_by_timezone(
                template_id,
                audience_filter,
                payload,
                scheduled_local_datetime,
                created_by,
            )

        admin_mailing_id = uuid4()
        await self._publish_pending(
            admin_mailing_id, template_id, audience_filter, payload
        )
        mailing = await self.mailing_repo.create(
            admin_mailing_id,
            template_id,
            audience_filter,
            payload,
            "sending",
            None,
            created_by,
        )
        return [mailing]

    async def _create_bucketed_by_timezone(
        self,
        template_id: UUID,
        audience_filter: dict[str, Any],
        payload: dict[str, Any],
        scheduled_local_datetime: datetime,
        created_by: UUID,
    ) -> list[AdminMailing]:
        """Разбить рассылку на несколько физических рассылок, по одной на каждую
        таймзону, встречающуюся у аудитории, подходящей под audience_filter.
        Создаются одной транзакцией — либо все бакеты, либо ни одного."""
        timezones = await search_distinct_timezones(audience_filter)
        rows = []
        for tz_name in timezones:
            scheduled_at = _local_datetime_to_utc(
                scheduled_local_datetime, tz_name
            )
            if scheduled_at is None:
                continue
            bucket_filter = {**audience_filter, "timezone": tz_name}
            rows.append(
                (
                    uuid4(),
                    template_id,
                    bucket_filter,
                    payload,
                    "scheduled",
                    scheduled_at,
                    created_by,
                )
            )
        if not rows:
            return []
        return await self.mailing_repo.create_many(rows)

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
