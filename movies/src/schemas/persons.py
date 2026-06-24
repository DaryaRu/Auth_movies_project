"""Person models for API responses."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PersonFilmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    uuid: UUID = Field(validation_alias="id")
    roles: list[str]


class Person(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    full_name: str = Field(validation_alias="name")
    films: list[PersonFilmResponse]


class PersonShort(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    full_name: str = Field(validation_alias="name")


PersonResponse = Person
