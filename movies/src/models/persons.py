"""Internal person models."""

from uuid import UUID

from pydantic import BaseModel


class PersonFilmShort(BaseModel):
    id: UUID
    roles: list[str]


class Person(BaseModel):
    id: UUID
    name: str
    films: list[PersonFilmShort] = []
