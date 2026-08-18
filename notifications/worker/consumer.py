"""Консьюмер notification-ready (рендер шаблона и отправка).

Использование deduplication_key защищает от повторной отправки одного и того же Kafka-сообщения (at least once).

AckPolicy.NACK_ON_ERROR: при успехе оффсет коммитится. При необработанном
исключении — nack (consumer.seek() назад на оффсет этого же сообщения), оффсет
не коммитится, то же сообщение будет вычитано повторно.
"""

from typing import Any
from uuid import UUID

from contacts import get_email
from core.settings import settings
from faststream import AckPolicy, Logger
from faststream.kafka import KafkaBroker
from pydantic import BaseModel, ValidationError
from render import render
from repositories.notifications import NotificationsRepository
from repositories.templates import TemplateRepository
from repositories.user_notification_settings import (
    UserNotificationSettingsRepository,
)
from senders import SENDERS

broker = KafkaBroker(settings.kafka_brokers_list)

templates_repo = TemplateRepository()
settings_repo = UserNotificationSettingsRepository()
notifications_repo = NotificationsRepository()


class ReadyMessage(BaseModel):
    """Схема сообщения из notification-ready."""

    user_id: UUID
    template_id: UUID
    payload: dict[str, Any] = {}
    channel: str
    deduplication_key: str


def _channel_enabled(
    settings_row: dict[str, Any] | None, channel: str
) -> bool:
    """Проверка, разрешен ли канал получателю. Отсутствие записи трактуется как email/push включены, sms — нет."""
    defaults = {"email": True, "sms": False, "push": True}
    if settings_row is None:
        return defaults.get(channel, False)
    if not settings_row["notifications_enabled"]:
        return False
    return bool(
        settings_row.get(f"{channel}_enabled", defaults.get(channel, False))
    )


def _parse_message(raw: dict, logger: Logger) -> ReadyMessage | None:
    """Провалидировать сырое сообщение. None, если некорректное сообщение, ретраить бессмысленно."""
    try:
        return ReadyMessage.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            f"Некорректное сообщение в {settings.KAFKA_READY_TOPIC}: {exc}"
        )
        return None


async def _get_or_create_notification(
    message: ReadyMessage, template: dict[str, Any] | None
) -> tuple[dict[str, Any], bool]:
    """Идемпотентно создать/получить строку в notifications."""
    notification_type = template["code"] if template else None
    return await notifications_repo.get_or_create(
        deduplication_key=message.deduplication_key,
        user_id=message.user_id,
        notification_type=notification_type,
        template_id=message.template_id,
        channel=message.channel,
        payload=message.payload,
    )


async def _check_deliverable(
    message: ReadyMessage,
    template: dict[str, Any] | None,
    notification_id: UUID,
    logger: Logger,
) -> bool:
    """Проверяет, что можно рендерить и слать дальше сообщение, если шаблон активен,
    отправитель зарегистрирован и уведомления по каналу разрешены.
    Если нет, notification помечается как failed/skipped, ретраить его нет смысла."""
    if template is None or not template["is_active"]:
        error = f"template {message.template_id} not found or inactive"
        await notifications_repo.mark_notification_failed(
            notification_id, error
        )
        logger.error(error)
        return False

    if message.channel not in SENDERS:
        error = f"no sender registered for channel={message.channel}"
        await notifications_repo.mark_notification_failed(
            notification_id, error
        )
        logger.error(f"{notification_id}: {error}")
        return False

    settings_row = await settings_repo.get_by_user_id(message.user_id)
    if not _channel_enabled(settings_row, message.channel):
        await notifications_repo.mark_notification_skipped(notification_id)
        logger.info(
            f"Канал {message.channel} отключён для {message.user_id}, пропускаю"
        )
        return False

    return True


async def _render_and_send(
    message: ReadyMessage,
    template: dict[str, Any],
    notification_id: UUID,
    logger: Logger,
) -> None:
    """Получает email, рендерит шаблон и отправляет.
    В случае исключения mark_notification_failed и raise, чтобы NACK_ON_ERROR не закоммитил
    оффсет и сообщение пришло снова."""
    try:
        email = await get_email(message.user_id)
        if email is None:
            await notifications_repo.mark_notification_failed(
                notification_id, f"no email for user {message.user_id}"
            )
            logger.error(f"{notification_id}: нет email у {message.user_id}")
            return

        subject = render(template["subject"], message.payload)
        body = render(template["body"], message.payload)
        await SENDERS[message.channel].send(email, subject, body)
    except Exception as exc:
        # TODO: DLQ.
        await notifications_repo.mark_notification_failed(
            notification_id, str(exc)
        )
        logger.warning(
            f"{notification_id}: отправка не удалась, будет повторена: {exc}"
        )
        raise

    await notifications_repo.mark_notification_sent(notification_id, email)
    logger.info(f"{notification_id}: отправлено")


@broker.subscriber(
    settings.KAFKA_READY_TOPIC,
    group_id=settings.KAFKA_WORKER_GROUP_ID,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def handle_ready(raw: dict, logger: Logger) -> None:
    """Обработать сообщение из notification-ready."""
    message = _parse_message(raw, logger)
    if message is None:
        return

    template = await templates_repo.get_by_id(message.template_id)
    notification, created = await _get_or_create_notification(
        message, template
    )
    notification_id = notification["notification_id"]

    if not created and notification["status"] in ("sent", "skipped"):
        logger.info(
            f"{notification_id} уже обработано (status={notification['status']}), пропускаю"
        )
        return

    if not await _check_deliverable(
        message, template, notification_id, logger
    ):
        return

    assert template is not None
    await _render_and_send(message, template, notification_id, logger)
