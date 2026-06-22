"""Genre model for API responses."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    uuid: UUID = Field(validation_alias="id")
    name: str
