#!/usr/bin/env python3
"""Скрипт для ручной проверки сообщений в notification.dlq."""

import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer

KAFKA_BROKERS = os.environ.get(
    "KAFKA_BROKERS", "kafka-0:9092,kafka-1:9092,kafka-2:9092"
)
TOPIC = os.environ.get("KAFKA_DLQ_TOPIC", "notification.dlq")


async def main() -> None:
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        group_id="verify-dlq-topic",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    print(f"Проверка {TOPIC} ({KAFKA_BROKERS}). Ctrl+C для остановки.")
    try:
        async for msg in consumer:
            value = json.loads(msg.value.decode())
            print(f"[offset={msg.offset}] {value}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
