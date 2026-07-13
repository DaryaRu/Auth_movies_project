from fastapi import APIRouter
from fastapi.responses import Response

from src.schemas.event import EventResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events/", status_code=202)
async def create_event(event: EventResponse) -> Response:
    return Response(status_code=202)
