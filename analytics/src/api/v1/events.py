import logging
from asyncio import QueueFull

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response

from src.api.v1.dependencies import CurrentUserDep
from src.core.config import settings
from src.core.limiter import limiter
from src.db import kafka
from src.schemas.event import EventResponseIn

router = APIRouter(prefix="/analytics", tags=["analytics"])

logger = logging.getLogger(__name__)


@router.post("/events/", status_code=202)
@limiter.limit(settings.EVENTS_RATE_LIMIT)
async def create_event(request: Request, event: EventResponseIn, user_id: CurrentUserDep) -> Response:
    message = {"user_id": str(user_id), **event.model_dump(mode="json")}
    try:
        kafka.buffer.put_nowait(message)
    except QueueFull:
        logger.error("Kafka buffer is full, rejecting event: type=%s", event.event_type)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable")
    return Response(status_code=202)
