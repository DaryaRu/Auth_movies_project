from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


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
    film_progress = "film_progress"
    video_quality_changed = "video_quality_changed"
    film_start = "film_start"
    video_completed = "video_completed"
    player_action = "player_action"


class EmptyPayload(BaseModel):
    """Payload для событий без дополнительных данных."""

    pass


class SearchFilterUsedPayload(BaseModel):
    """Payload для search_filter_used: применённые сортировка и фильтр по жанру."""

    genre: UUID | None = None
    sort: Literal["imdb_rating", "-imdb_rating"] | None = None


class FilmSearchPayload(BaseModel):
    """Payload для film_search: текст поискового запроса."""

    query: str


class PageTimeSpentPayload(BaseModel):
    """Payload для page_time_spent: сколько секунд пользователь провёл на странице."""

    page: str
    seconds: int = Field(ge=0)


class FilmProgressPayload(BaseModel):
    """Payload для film_progress: позиция и длительность просмотра фильма."""

    viewed_frame: int = Field(ge=0)
    movie_duration: int = Field(ge=0)


class VideoQualityChangedPayload(BaseModel):
    """Payload для video_quality_changed: смена качества видео."""

    old_quality: str
    new_quality: str


class PlayerActionPayload(BaseModel):
    """Payload для player_action: действие пользователя в плеере."""

    action: Literal["play", "pause", "seek"]
    position_sec: int | None = Field(default=None, ge=0)


class BaseEvent(BaseModel):
    user_id: UUID
    object_id: UUID | None = None
    event_time: datetime


class FilmViewEvent(BaseEvent):
    event_type: Literal[EventType.film_view] = EventType.film_view
    payload: EmptyPayload = EmptyPayload()


class FilmsListViewEvent(BaseEvent):
    event_type: Literal[EventType.films_list_view] = EventType.films_list_view
    payload: EmptyPayload = EmptyPayload()


class FilmSearchEvent(BaseEvent):
    event_type: Literal[EventType.film_search] = EventType.film_search
    payload: FilmSearchPayload


class GenreViewEvent(BaseEvent):
    event_type: Literal[EventType.genre_view] = EventType.genre_view
    payload: EmptyPayload = EmptyPayload()


class PersonViewEvent(BaseEvent):
    event_type: Literal[EventType.person_view] = EventType.person_view
    payload: EmptyPayload = EmptyPayload()


class PersonFilmsViewEvent(BaseEvent):
    event_type: Literal[EventType.person_films_view] = (
        EventType.person_films_view
    )
    payload: EmptyPayload = EmptyPayload()


class SearchFilterUsedEvent(BaseEvent):
    event_type: Literal[EventType.search_filter_used] = (
        EventType.search_filter_used
    )
    payload: SearchFilterUsedPayload


class TrailerClickEvent(BaseEvent):
    event_type: Literal[EventType.trailer_click] = EventType.trailer_click
    payload: EmptyPayload = EmptyPayload()


class PageTimeSpentEvent(BaseEvent):
    event_type: Literal[EventType.page_time_spent] = EventType.page_time_spent
    payload: PageTimeSpentPayload


class FilmProgressEvent(BaseEvent):
    event_type: Literal[EventType.film_progress] = EventType.film_progress
    payload: FilmProgressPayload


class VideoQualityChangedEvent(BaseEvent):
    event_type: Literal[EventType.video_quality_changed] = (
        EventType.video_quality_changed
    )
    payload: VideoQualityChangedPayload


class FilmStartEvent(BaseEvent):
    event_type: Literal[EventType.film_start] = EventType.film_start
    payload: EmptyPayload = EmptyPayload()


class VideoCompletedEvent(BaseEvent):
    event_type: Literal[EventType.video_completed] = EventType.video_completed
    payload: EmptyPayload = EmptyPayload()


class PlayerActionEvent(BaseEvent):
    event_type: Literal[EventType.player_action] = EventType.player_action
    payload: PlayerActionPayload


EventResponseIn = Annotated[
    Union[
        FilmViewEvent,
        FilmsListViewEvent,
        FilmSearchEvent,
        GenreViewEvent,
        PersonViewEvent,
        PersonFilmsViewEvent,
        SearchFilterUsedEvent,
        TrailerClickEvent,
        PageTimeSpentEvent,
        FilmProgressEvent,
        VideoQualityChangedEvent,
        FilmStartEvent,
        VideoCompletedEvent,
        PlayerActionEvent,
    ],
    Field(discriminator="event_type"),
]
