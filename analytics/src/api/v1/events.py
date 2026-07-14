import logging
from asyncio import QueueFull
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from src.api.v1.dependencies import CurrentUserDep
from src.db import kafka
from src.schemas.event import EventResponseIn, EventResponseOut

router = APIRouter(prefix="/analytics", tags=["analytics"])

logger = logging.getLogger(__name__)


@router.post("/events/", status_code=202)
async def create_event(event: EventResponseIn, user_id: CurrentUserDep) -> Response:
    event_out = EventResponseOut(
        user_id=user_id,
        event_type=event.event_type,
        object_id=event.object_id,
        payload=event.payload,
        event_time=event.event_time,
        timestamp=datetime.now(timezone.utc),
    )
    try:
        kafka.buffer.put_nowait(event_out.model_dump(mode="json"))
    except QueueFull:
        logger.error("Kafka buffer is full, rejecting event: type=%s", event.event_type)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable")
    return Response(status_code=202)
