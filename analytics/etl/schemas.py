from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventType(str, Enum):
    search_filter_used = "search_filter_used"
    trailer_click = "trailer_click"
    page_time_spent = "page_time_spent"
    film_progress = "film_progress"
    video_quality_changed = "video_quality_changed"
    film_start = "film_start"
    video_completed = "video_completed"
    player_action = "player_action"


class EventMessage(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")
        }
    )
    
    user_id: UUID
    event_type: EventType
    object_id: UUID | None
    payload: dict
    event_time: datetime
