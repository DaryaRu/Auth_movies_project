"""Инициализация Kafka producer.

Буфера нет: отправка синхронная относительно запроса — NotificationService.create_notification
дожидается подтверждения от Kafka (send_and_wait) прежде чем API ответит вызывающему.

Потеря события недопустима, поэтому продюсер использует acks=settings.KAFKA_ACKS
(по умолчанию "all"), т.е. подтверждение приходит только после записи на все реплики,
а не только от лидера партиции (! не гарантирует без min.insync.replicas > 1 на топике
(kafka-topic-init-notifications в docker-compose.yml) —
если min.insync.replicas=1, ISR может состоять из одного лидера. В dev (KAFKA_MIN_INSYNC_REPLICAS=1, KAFKA_REPLICATION_FACTOR=1)
реальной защиты от потери при падении лидера нет — появляется только в проде
(KAFKA_MIN_INSYNC_REPLICAS=2, KAFKA_REPLICATION_FACTOR=3).
"""

import asyncio
import logging

from aiokafka import AIOKafkaProducer

from src.core.config import settings
from src.db import kafka

logger = logging.getLogger(__name__)


async def init_kafka() -> None:
    """Создать и подключить Kafka producer с ретраями, если брокер ещё не готов."""
    kafka.producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BROKERS, acks=settings.KAFKA_ACKS
    )
    while True:
        try:
            await kafka.producer.start()
            logger.info("Kafka producer connected")
            return
        except Exception as e:
            logger.warning(
                "Kafka unavailable, retrying in %ds: %s",
                settings.KAFKA_RETRY_INTERVAL_SEC,
                e,
            )
            await asyncio.sleep(settings.KAFKA_RETRY_INTERVAL_SEC)


async def close_kafka() -> None:
    """Остановить Kafka producer."""
    if kafka.producer is not None:
        await kafka.producer.stop()
        logger.info("Kafka producer stopped")
