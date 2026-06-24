"""Models for ETL."""

from uuid import UUID

from pydantic import BaseModel, Field


class PersonFilm(BaseModel):
    id: UUID
    roles: list[str]


class Person(BaseModel):
    id: UUID
    name: str
    films: list[PersonFilm] = []


class FilmPerson(BaseModel):
    id: UUID
    name: str


class Genre(BaseModel):
    id: UUID
    name: str


class FilmWork(BaseModel):
    id: UUID
    imdb_rating: float | None = None
    genres: list[Genre] = Field(default_factory=list)
    title: str
    description: str | None = None
    directors_names: list[str] = Field(default_factory=list)
    actors_names: list[str] = Field(default_factory=list)
    writers_names: list[str] = Field(default_factory=list)
    directors: list[FilmPerson] = Field(default_factory=list)
    actors: list[FilmPerson] = Field(default_factory=list)
    writers: list[FilmPerson] = Field(default_factory=list)
