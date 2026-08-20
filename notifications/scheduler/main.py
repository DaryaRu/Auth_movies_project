"""Шедулер.

Периодически проверяет notification_triggers и admin_mailings,
публикует сообщения в Kafka-топик notification-pending.
"""

import asyncio
import json
import logging
import sys

from aiokafka import AIOKafkaProducer
from core.settings import settings
from db.postgres import PostgreSQL
from repositories.admin_mailings import AdminMailingsRepository
from repositories.notification_triggers import NotificationTriggersRepository

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _init_producer() -> AIOKafkaProducer:
    """Создать и подключить Kafka producer с ретраями, если брокер пока не готов."""
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BROKERS, acks=settings.KAFKA_ACKS
    )
    while True:
        try:
            await producer.start()
            logger.info("Kafka producer connected")
            return producer
        except Exception as exc:
            logger.warning(
                "Kafka unavailable, retrying in %ds: %s",
                settings.KAFKA_RETRY_INTERVAL_SEC,
                exc,
            )
            await asyncio.sleep(settings.KAFKA_RETRY_INTERVAL_SEC)


class Scheduler:
    """Публикует в notification-pending триггеры/рассылки, которым пора сработать."""

    def __init__(
        self,
        triggers_repo: NotificationTriggersRepository,
        mailings_repo: AdminMailingsRepository,
        producer: AIOKafkaProducer,
    ):
        self.triggers_repo = triggers_repo
        self.mailings_repo = mailings_repo
        self.producer = producer

    async def _publish_pending(self, message: dict, key: str) -> None:
        await self.producer.send_and_wait(
            settings.KAFKA_PENDING_TOPIC,
            value=json.dumps(message).encode(),
            key=key.encode(),
        )

    async def process_triggers(self) -> None:
        """Проверяет триггеры, публикует сработавшие и отмечает все проверенные."""
        triggers = await self.triggers_repo.get_triggers_to_check()
        for trigger in triggers:
            try:
                last_sent = trigger["last_notification_sent"]
                if last_sent is None or trigger["last_update"] > last_sent:
                    await self._publish_pending(
                        {
                            "content_id": str(trigger["content_id"]),
                            "notification_type": trigger["notification_type"],
                            "template_id": str(trigger["template_id"]),
                            "payload": trigger["payload"],
                        },
                        key=str(trigger["trigger_id"]),
                    )
                    logger.info(
                        "Триггер %s/%s сработал, опубликован в %s",
                        trigger["content_id"],
                        trigger["notification_type"],
                        settings.KAFKA_PENDING_TOPIC,
                    )
                await self.triggers_repo.mark_trigger_checked(
                    trigger["trigger_id"]
                )
            except Exception:
                logger.exception(
                    "Не удалось обработать триггер %s", trigger["trigger_id"]
                )

    async def process_mailings(self) -> None:
        """Публикует рассылки, у которых наступил scheduled_at, и переводит их в sending."""
        mailings = await self.mailings_repo.get_due_scheduled_mailings()
        for mailing in mailings:
            try:
                await self._publish_pending(
                    {
                        "admin_mailing_id": str(mailing["admin_mailing_id"]),
                        "template_id": str(mailing["template_id"]),
                        "audience_filter": mailing["audience_filter"],
                        "payload": mailing["payload"],
                    },
                    key=str(mailing["admin_mailing_id"]),
                )
                await self.mailings_repo.mark_mailing_sending(
                    mailing["admin_mailing_id"]
                )
                logger.info(
                    "Рассылка %s опубликована в %s",
                    mailing["admin_mailing_id"],
                    settings.KAFKA_PENDING_TOPIC,
                )
            except Exception:
                logger.exception(
                    "Не удалось обработать рассылку %s",
                    mailing["admin_mailing_id"],
                )

    async def run_once(self) -> None:
        """Один проход: notification_triggers, потом admin_mailings."""
        await self.process_triggers()
        await self.process_mailings()


async def main() -> None:
    await PostgreSQL.connect()
    producer = await _init_producer()
    scheduler = Scheduler(
        NotificationTriggersRepository(), AdminMailingsRepository(), producer
    )
    try:
        while True:
            try:
                await scheduler.run_once()
            except Exception:
                logger.exception(
                    "Сбой в цикле шедулера — повтор через %ds",
                    settings.POLL_INTERVAL_SEC,
                )
            await asyncio.sleep(settings.POLL_INTERVAL_SEC)
    finally:
        await producer.stop()
        await PostgreSQL.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
