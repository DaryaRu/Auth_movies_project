import asyncio
from typing import Optional

from aiokafka import AIOKafkaProducer

producer: Optional[AIOKafkaProducer] = None
buffer: Optional[asyncio.Queue] = None
task: Optional[asyncio.Task] = None
