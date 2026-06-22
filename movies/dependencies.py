"""Composition Root."""

from elasticsearch import AsyncElasticsearch
from fastapi import Depends

from core import config
from db.elastic import get_elastic
from repositories.films import FilmRepository
from repositories.genres import GenresRepository
from repositories.persons import PersonsRepository
from services.film import FilmService
from services.genres import GenreService
from services.persons import PersonService


def get_film_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    """Dependency provider for FilmService instantiation."""
    repository = FilmRepository(elastic, index=config.ELASTIC_FILM_INDEX)
    return FilmService(repository)


def get_genre_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    """Dependency provider for GenreService instantiation."""
    repository = GenresRepository(elastic, index=config.ELASTIC_GENRE_INDEX)
    return GenreService(repository)


def get_person_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    """Dependency provider for PersonService instantiation."""
    person_repo = PersonsRepository(elastic, index=config.ELASTIC_PERSON_INDEX)
    film_repo = FilmRepository(elastic, index=config.ELASTIC_FILM_INDEX)
    return PersonService(person_repo=person_repo, movie_repo=film_repo)
