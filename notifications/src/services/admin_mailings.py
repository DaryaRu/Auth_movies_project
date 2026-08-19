"""Сервис для ручных рассылок из админки (Scheduled group / Immediate group)."""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from aiokafka.errors import KafkaError

from src.core.config import settings
from src.db import kafka
from src.repositories.admin_mailings import AdminMailingRepository
from src.repositories.templates import TemplateRepository
from src.schemas.admin_mailings import AdminMailing
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)


class InvalidScheduledAtError(Exception):
    """scheduled_at указан неверно (задавать в будущем)."""


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
        created_by: UUID,
    ) -> AdminMailing:
        """Создать рассылку.

        Если scheduled_at не задан, то отправка происходит сразу (Immediate group): запись
        создается сразу со status=sending, публикуется в notification-pending.
        scheduled_at задавать в будущем, status=scheduled.
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

        status = "scheduled" if scheduled_at is not None else "sending"

        mailing = await self.mailing_repo.create(
            template_id,
            audience_filter,
            payload,
            status,
            scheduled_at,
            created_by,
        )

        if status == "sending":
            await self._publish_pending(mailing)

        return mailing

    async def _publish_pending(self, mailing: AdminMailing) -> None:
        """Опубликовать неполное сообщение в notification-pending. А резолв
        аудитории по audience_filter и реальную отправку делает воркер."""
        message = {
            "admin_mailing_id": str(mailing.admin_mailing_id),
            "template_id": str(mailing.template_id),
            "audience_filter": mailing.audience_filter,
            "payload": mailing.payload,
        }
        assert kafka.producer is not None
        try:
            await kafka.producer.send_and_wait(
                settings.KAFKA_PENDING_TOPIC,
                value=json.dumps(message).encode(),
                key=str(mailing.admin_mailing_id).encode(),
            )
        except KafkaError as e:
            raise RuntimeError(
                f"Failed to publish admin mailing to Kafka: {e}"
            ) from e
