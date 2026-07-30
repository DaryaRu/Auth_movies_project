"""Internal film model."""

from datetime import date
from uuid import UUID

from models.genres import Genre
from models.persons import Person
from pydantic import BaseModel


class FilmShort(BaseModel):
    id: UUID
    title: str
    imdb_rating: float | None = None


class Film(BaseModel):
    id: UUID
    title: str
    imdb_rating: float | None = None
    description: str | None = None
    creation_date: date | None = None
    subscription_level: int = 0
    genres: list[Genre] = []
    directors: list[Person] = []
    actors: list[Person] = []
    writers: list[Person] = []
    file_path: str | None = None
