"""Консьюмер notification-ready, notification-ready-bulk и notification-pending (рендер шаблона и отправка).

Использование deduplication_key защищает от повторной отправки одного и того же Kafka-сообщения (at least once).

AckPolicy.NACK_ON_ERROR: при успехе оффсет коммитится. При необработанном
исключении — nack, оффсет не коммитится, сообщение будет вычитано повторно. Сбой отправки конкретному
получателю (_render_and_send) уходит в DLQ (notification.dlq), чтобы не блокировать Kafka.
"""

import asyncio
from typing import Any
from uuid import UUID

from audience import search_bookmark_users, search_users
from contacts import get_email
from core.settings import settings
from faststream import AckPolicy, Logger
from faststream.kafka import KafkaBroker
from pydantic import BaseModel, ValidationError
from render import render
from repositories.admin_mailings import AdminMailingsRepository
from repositories.notification_triggers import NotificationTriggersRepository
from repositories.notifications import NotificationsRepository
from repositories.templates import TemplateRepository
from repositories.user_notification_settings import (
    UserNotificationSettingsRepository,
)
from senders import SENDERS

broker = KafkaBroker(settings.kafka_brokers_list)
dlq_publisher = broker.publisher(settings.KAFKA_DLQ_TOPIC)
ready_bulk_publisher = broker.publisher(settings.KAFKA_READY_BULK_TOPIC)

templates_repo = TemplateRepository()
settings_repo = UserNotificationSettingsRepository()
notifications_repo = NotificationsRepository()
admin_mailings_repo = AdminMailingsRepository()
notification_triggers_repo = NotificationTriggersRepository()


async def _backoff_before_retry() -> None:
    """Фиксированная задержка перед повторной доставкой сообщения через NACK."""
    await asyncio.sleep(settings.KAFKA_RETRY_BACKOFF_TIME)


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


def _parse_message(
    raw: dict, logger: Logger, source_topic: str
) -> ReadyMessage | None:
    """Провалидировать сырое сообщение. None, если некорректное сообщение, ретраить бессмысленно."""
    try:
        return ReadyMessage.model_validate(raw)
    except ValidationError as exc:
        logger.error(f"Некорректное сообщение в {source_topic}: {exc}")
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
    source_topic: str,
) -> None:
    """Получает email, рендерит шаблон и отправляет.
    В случае исключения помечает notification failed и публикует в DLQ,
    не пробрасывает исключение дальше.
    """
    try:
        subject = render(template["subject"], message.payload)
        body = render(template["body"], message.payload)

        if message.channel == "push":
            delivery_address = str(message.user_id)
        else:
            email = await get_email(message.user_id)
            if email is None:
                await notifications_repo.mark_notification_failed(
                    notification_id, f"no email for user {message.user_id}"
                )
                logger.error(f"{notification_id}: нет email у {message.user_id}")
                return
            delivery_address = email

        await SENDERS[message.channel].send(delivery_address, subject, body)
    except Exception as exc:
        await notifications_repo.mark_notification_failed(
            notification_id, str(exc)
        )
        logger.warning(
            f"{notification_id}: отправка не удалась, публикуется в {settings.KAFKA_DLQ_TOPIC}: {exc}"
        )
        await dlq_publisher.publish(
            {
                "source_topic": source_topic,
                "notification_id": str(notification_id),
                "message": message.model_dump(mode="json"),
                "error": str(exc),
            }
        )
        return

    await notifications_repo.mark_notification_sent(notification_id, delivery_address)
    logger.info(f"{notification_id}: отправлено")


async def _process_ready_message(
    raw: dict, logger: Logger, source_topic: str
) -> None:
    """Общая обработка notification-ready/notification-ready-bulk: рендер и отправка."""
    message = _parse_message(raw, logger, source_topic)
    if message is None:
        return

    try:
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
        await _render_and_send(
            message, template, notification_id, logger, source_topic
        )
    except Exception:
        await _backoff_before_retry()
        raise


@broker.subscriber(
    settings.KAFKA_READY_TOPIC,
    group_id=settings.KAFKA_WORKER_GROUP_ID,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def handle_ready(raw: dict, logger: Logger) -> None:
    """Обработать сообщение из notification-ready (персональные уведомления)."""
    await _process_ready_message(raw, logger, settings.KAFKA_READY_TOPIC)


@broker.subscriber(
    settings.KAFKA_READY_BULK_TOPIC,
    group_id=settings.KAFKA_WORKER_GROUP_ID,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def handle_ready_bulk(raw: dict, logger: Logger) -> None:
    """Обработать сообщение из notification-ready-bulk (fan-out массовых рассылок)."""
    await _process_ready_message(raw, logger, settings.KAFKA_READY_BULK_TOPIC)


class AdminMailingMessage(BaseModel):
    """Схема сообщения из notification-pending, опубликованного admin_mailings."""

    admin_mailing_id: UUID
    template_id: UUID
    audience_filter: dict[str, Any] = {}
    payload: dict[str, Any] = {}


async def _handle_admin_mailing(raw: dict, logger: Logger) -> None:
    try:
        message = AdminMailingMessage.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            f"Некорректное сообщение admin_mailing в {settings.KAFKA_PENDING_TOPIC}: {exc}"
        )
        return

    template = await templates_repo.get_by_id(message.template_id)
    if template is None or not template["is_active"]:
        await admin_mailings_repo.mark_mailing_failed(message.admin_mailing_id)
        logger.error(
            f"{message.admin_mailing_id}: шаблон {message.template_id} не найден/неактивен"
        )
        return

    try:
        user_ids = await search_users(message.audience_filter)
    except Exception as exc:
        # Резолв не удался до начала прохода по получателям — вся рассылка failed.
        await admin_mailings_repo.mark_mailing_failed(message.admin_mailing_id)
        logger.warning(
            f"{message.admin_mailing_id}: не удалось резолвить аудиторию, будет повторено: {exc}"
        )
        raise

    logger.info(
        f"{message.admin_mailing_id}: аудитория — {len(user_ids)} получателей"
    )

    for user_id in user_ids:
        ready_message = ReadyMessage(
            user_id=user_id,
            template_id=message.template_id,
            payload=message.payload,
            channel=template["channel"],
            deduplication_key=f"{message.admin_mailing_id}:{user_id}",
        )
        await ready_bulk_publisher.publish(
            ready_message.model_dump(mode="json"), key=str(user_id).encode()
        )

    await admin_mailings_repo.mark_mailing_sent(message.admin_mailing_id)
    logger.info(
        f"{message.admin_mailing_id}: {len(user_ids)} сообщений опубликовано в {settings.KAFKA_READY_BULK_TOPIC}"
    )


class NotificationTriggerMessage(BaseModel):
    """Схема сообщения из notification-pending, опубликованного notification_triggers."""

    content_id: UUID
    notification_type: str
    template_id: UUID
    payload: dict[str, Any] = {}


async def _handle_notification_trigger(raw: dict, logger: Logger) -> None:
    """Резолв аудитории по закладкам, отправка в notification-ready-bulk."""
    try:
        message = NotificationTriggerMessage.model_validate(raw)
    except ValidationError as exc:
        logger.error(
            f"Некорректное сообщение notification_trigger в {settings.KAFKA_PENDING_TOPIC}: {exc}"
        )
        return

    trigger = await notification_triggers_repo.get_by_content_and_type(
        message.content_id, message.notification_type
    )
    if trigger is None or not trigger["is_active"]:
        logger.error(
            f"{message.content_id}/{message.notification_type}: триггер не найден/неактивен"
        )
        return

    template = await templates_repo.get_by_id(message.template_id)
    if template is None or not template["is_active"]:
        logger.error(
            f"{message.content_id}/{message.notification_type}: шаблон {message.template_id} не найден/неактивен"
        )
        return

    try:
        user_ids = await search_bookmark_users(message.content_id)
    except Exception as exc:
        logger.warning(
            f"{message.content_id}/{message.notification_type}: не удалось резолвить аудиторию, будет повторено: {exc}"
        )
        raise

    logger.info(
        f"{message.content_id}/{message.notification_type}: аудитория — {len(user_ids)} получателей"
    )

    trigger_last_update = trigger["last_update"].isoformat()
    for user_id in user_ids:
        ready_message = ReadyMessage(
            user_id=user_id,
            template_id=message.template_id,
            payload=message.payload,
            channel=template["channel"],
            deduplication_key=f"{trigger['trigger_id']}:{trigger_last_update}:{user_id}",
        )
        await ready_bulk_publisher.publish(
            ready_message.model_dump(mode="json"), key=str(user_id).encode()
        )

    await notification_triggers_repo.mark_trigger_sent(trigger["trigger_id"])
    logger.info(
        f"{message.content_id}/{message.notification_type}: {len(user_ids)} сообщений опубликовано в {settings.KAFKA_READY_BULK_TOPIC}"
    )


@broker.subscriber(
    settings.KAFKA_PENDING_TOPIC,
    group_id=settings.KAFKA_WORKER_GROUP_ID,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def handle_pending(raw: dict, logger: Logger) -> None:
    """Обработать сообщение из notification-pending."""
    try:
        if "admin_mailing_id" in raw:
            await _handle_admin_mailing(raw, logger)
        elif "content_id" in raw:
            await _handle_notification_trigger(raw, logger)
        else:
            logger.error(
                f"Неизвестная форма сообщения в {settings.KAFKA_PENDING_TOPIC}: {raw}"
            )
    except Exception:
        await _backoff_before_retry()
        raise
