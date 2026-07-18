from faststream import Logger
from faststream.kafka import KafkaBroker

from schemas import EventMessage, EventType
import core.dependiences as deps
from core.settings import settings
from transformers import EventTransformer

broker = KafkaBroker(settings.kafka_brokers_list)
dlq_publisher = broker.publisher(
    settings.KAFKA_DLQ_TOPIC
)


@broker.subscriber(settings.KAFKA_TOPIC)
async def consume(
    event: EventMessage,
    logger: Logger,
):
    if event.event_type != EventType.film_progress:
        return
    try:
        row = EventTransformer.transform(event)
        await deps.movie_views_repository.save(
            row.model_dump(mode="json")
        )
    except ValueError as exc:
        logger.error(f"Ошибка валидации данных: {exc}")
        await dlq_publisher.publish(
            {
                "event": event.model_dump(mode="json"),
                "error": str(exc),
            }
        )
    except Exception as exc:
        logger.error(f"Ошибка: {exc}")
        raise
