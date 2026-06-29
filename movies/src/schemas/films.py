"""Film model for API."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from schemas.genres import GenreResponse
from schemas.persons import PersonShort


class FilmResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    uuid: UUID = Field(validation_alias="id")
    title: str
    imdb_rating: float | None = None
    description: str | None = None
    creation_date: date | None = None
    subscription_level: int = 0
    directors: list[PersonShort] = []
    actors: list[PersonShort] = []
    writers: list[PersonShort] = []
    genre: list[GenreResponse] = Field(default=[], validation_alias="genres")
    file_path: str | None = None
