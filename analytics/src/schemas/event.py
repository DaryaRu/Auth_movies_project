from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class EventType(str, Enum):
    film_view = "film_view"
    films_list_view = "films_list_view"
    film_search = "film_search"
    genre_view = "genre_view"
    person_view = "person_view"
    person_films_view = "person_films_view"
    search_filter_used = "search_filter_used"
    trailer_click = "trailer_click"
    page_time_spent = "page_time_spent"
    # Требует сервиса видеостриминга:
    # video_quality_changed = "video_quality_changed"
    # video_completed = "video_completed"
    # player_action = "player_action"
    # film_start = "film_start"
    # film_end = "film_end"
    # film_progress = "film_progress"


class EventResponse(BaseModel):
    event_type: EventType
    object_id: UUID | None = None
    payload: dict = {}
