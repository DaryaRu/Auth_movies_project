"""FilmShort model for API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FilmShortResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    uuid: UUID = Field(validation_alias="id")
    title: str
    imdb_rating: Optional[float] = None
