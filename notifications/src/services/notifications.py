"""Сервис для персональных уведомлений."""

import json
from uuid import UUID

from aiokafka.errors import KafkaError

from src.core.config import settings
from src.db import kafka
from src.repositories.templates import TemplateRepository


class TemplateNotFoundError(Exception):
    """Шаблон не найден или неактивен."""


class InvalidPayloadError(Exception):
    """payload содержит переменные, не разрешённые шаблоном."""

    def __init__(self, unknown_keys: set[str]):
        self.unknown_keys = unknown_keys
        super().__init__(f"Unknown payload keys: {sorted(unknown_keys)}")


class NotificationService:
    """Сервис для создания персональных уведомлений."""

    def __init__(self, template_repository: TemplateRepository):
        self.template_repo = template_repository

    async def create_notification(
        self, user_id: UUID, template_id: UUID, payload: dict
    ) -> None:
        """Провалидировать и опубликовать персональное уведомление в notification-ready."""
        template = await self.template_repo.get_by_id(template_id)
        if template is None or not template.is_active:
            raise TemplateNotFoundError(str(template_id))

        if template.allowed_variables:
            unknown_keys = set(payload.keys()) - set(
                template.allowed_variables
            )
            if unknown_keys:
                raise InvalidPayloadError(unknown_keys)

        message = {
            "user_id": str(user_id),
            "template_id": str(template_id),
            "payload": payload,
            "channel": template.channel,
        }
        assert kafka.producer is not None
        try:
            await kafka.producer.send_and_wait(
                settings.KAFKA_READY_TOPIC,
                value=json.dumps(message).encode(),
                key=str(user_id).encode(),
            )
        except KafkaError as e:
            raise RuntimeError(
                f"Failed to publish notification to Kafka: {e}"
            ) from e
