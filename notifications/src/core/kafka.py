"""Инициализация Kafka producer."""

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
