from faststream import AckPolicy, Logger
from faststream.kafka import KafkaBroker
from pydantic import TypeAdapter, ValidationError

from schemas import EventResponseIn
import core.dependiences as deps
from core.settings import settings

broker = KafkaBroker(
    settings.kafka_brokers_list,
    retry_backoff_ms=settings.KAFKA_RETRY_BACKOFF_MS,
)
dlq_publisher = broker.publisher(
    settings.KAFKA_DLQ_TOPIC
)

_event_adapter = TypeAdapter(EventResponseIn)


@broker.subscriber(
    settings.KAFKA_TOPIC,
    group_id=settings.KAFKA_GROUP_ID,
    ack_policy=AckPolicy.ACK_FIRST,
)
async def consume(
    payload: dict,
    logger: Logger,
):
    try:
        event = _event_adapter.validate_python(payload)
    except ValidationError as exc:
        logger.error(f"Ошибка валидации данных: {exc}")
        await dlq_publisher.publish(
            {
                "event": payload,
                "error": str(exc),
            }
        )
        return

    try:
        await deps.movie_views_repository.save(
            event.model_dump(mode="json")
        )
    except Exception as exc:
        logger.error(f"Ошибка: {exc}")
        await dlq_publisher.publish(
            {
                "event": payload,
                "error": str(exc),
            }
        )
