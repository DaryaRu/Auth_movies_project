"""Kafka producer."""

from typing import Optional

from aiokafka import AIOKafkaProducer

producer: Optional[AIOKafkaProducer] = None
