"""Сервис для триггеров уведомлений (Scheduled group)."""

from typing import Any
from uuid import UUID

from src.repositories.notification_triggers import (
    NotificationTriggerRepository,
)
from src.repositories.templates import TemplateRepository
from src.schemas.triggers import NotificationTrigger
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)


class NotificationTriggerService:
    """Сервис для триггеров уведомлений."""

    def __init__(
        self,
        trigger_repository: NotificationTriggerRepository,
        template_repository: TemplateRepository,
    ):
        self.trigger_repo = trigger_repository
        self.template_repo = template_repository

    async def upsert(
        self,
        content_id: UUID,
        notification_type: str,
        template_id: UUID,
        payload: dict[str, Any],
    ) -> NotificationTrigger:
        """Cделать upsert по (content_id, notification_type)."""
        template = await self.template_repo.get_by_id(template_id)
        if template is None or not template.is_active:
            raise TemplateNotFoundError(str(template_id))

        unknown_keys = set(payload.keys()) - set(template.allowed_variables)
        if unknown_keys:
            raise InvalidPayloadError(unknown_keys)

        return await self.trigger_repo.upsert(
            content_id, notification_type, template_id, payload
        )
