import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from src.core.config import settings
from src.db import kafka

logger = logging.getLogger(__name__)

_RETRY_INTERVAL = settings.KAFKA_RETRY_INTERVAL_SEC


async def init_kafka() -> None:
    kafka.buffer = asyncio.Queue(maxsize=settings.KAFKA_BUFFER_SIZE)
    kafka.producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKERS, acks=settings.KAFKA_ACKS)
    kafka.task = asyncio.create_task(_worker())
    logger.info("Kafka producer initialized, worker started")


async def close_kafka() -> None:
    if kafka.task is not None and not kafka.task.done():
        kafka.task.cancel()
        try:
            await kafka.task
        except asyncio.CancelledError:
            pass
    if kafka.producer is not None:
        try:
            await kafka.producer.stop()
            logger.info("Kafka producer stopped")
        except Exception as e:
            logger.warning("Error stopping Kafka producer: %s", e)


async def _worker() -> None:
    await _connect()
    while True:
        event = await kafka.buffer.get()
        try:
            value = json.dumps(event).encode()
            key = str(event.get("user_id", "")).encode()
            await kafka.producer.send_and_wait(settings.KAFKA_TOPIC, value=value, key=key)
        except KafkaError as e:
            logger.error(
                "Failed to publish event to Kafka, event lost: type=%s error=%s",
                event.get("event_type"),
                e,
            )
            await _reconnect()
        finally:
            kafka.buffer.task_done()


async def _connect() -> None:
    while True:
        try:
            await kafka.producer.start()
            logger.info("Kafka producer connected")
            return
        except Exception as e:
            logger.warning("Kafka unavailable, retrying in %ds: %s", _RETRY_INTERVAL, e)
            await asyncio.sleep(_RETRY_INTERVAL)


async def _reconnect() -> None:
    logger.warning("Kafka connection lost, reconnecting...")
    try:
        await kafka.producer.stop()
    except Exception:
        pass
    kafka.producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKERS, acks=settings.KAFKA_ACKS)
    await _connect()
