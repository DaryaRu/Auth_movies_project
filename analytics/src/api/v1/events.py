from fastapi import APIRouter
from fastapi.responses import Response

from src.api.v1.dependencies import CurrentUserDep
from src.schemas.event import EventResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events/", status_code=202)
async def create_event(event: EventResponse, user_id: CurrentUserDep) -> Response:
    return Response(status_code=202)
