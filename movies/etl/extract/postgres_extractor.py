"""Extract data from PostgreSQL."""

import logging
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from typing import Literal, TypedDict
from uuid import UUID

import psycopg
from backoff import backoff
from config import Settings
from extract.queries import (
    FILM_WORK_DETAILS,
    FILM_WORK_GENRES,
    FILM_WORK_IDS_BY_GENRE,
    FILM_WORK_IDS_BY_PERSON,
    FILM_WORK_IDS_BY_SELF,
    FILM_WORK_PERSONS,
    GENRE_DETAILS,
    PERSON_DETAILS,
    query_changed_entities,
)
from psycopg.rows import dict_row
from transform.transformer import (
    build_film_work,
    build_genre,
    build_persons_from_rows,
    group_genres_by_film,
    group_persons_by_film,
)

from models import FilmWork, Genre, Person

logger = logging.getLogger(__name__)

ENTITY_TYPE_FILM_WORK = "film_work"
ENTITY_TYPE_GENRE = "genre"
ENTITY_TYPE_PERSON = "person"
DEFAULT_MODIFIED_VALUE = datetime.min
DEFAULT_ID_VALUE = "00000000-0000-0000-0000-000000000000"
EntityType = Literal["film_work", "genre", "person"]
RowData = dict[str, object]


class CheckpointState(TypedDict):
    """Checkpoint with modified and id values."""

    modified: str
    id: str


class PostgresExtractor:
    """Extract data from PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        """Initialize extractor with app settings."""
        self.settings = settings

    @backoff()
    def fetch_changed_entities(
        self,
        entity_type: EntityType,
        checkpoint_state: CheckpointState,
    ) -> list[RowData]:
        """Fetch changed entities after the checkpoint."""

        query = get_changed_entities_query(entity_type)
        with closing(
            psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row)
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    {
                        "modified": checkpoint_state["modified"],
                        "id": checkpoint_state["id"],
                        "limit": self.settings.etl_chunk_size,
                    },
                )
                result = list(cursor.fetchall())
                return result

    @backoff()
    def fetch_film_work_ids(
        self, entity_type: EntityType, entity_ids: list[UUID]
    ) -> list[UUID]:
        """Fetch film_work_ids affected by changed entities."""

        if not entity_ids:
            return []

        query = get_film_work_ids_query(entity_type)
        with closing(
            psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row)
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, {"entity_ids": entity_ids})
                rows = cursor.fetchall()
        result = [row["id"] for row in rows]
        return result

    @backoff()
    def fetch_film_works(self, film_work_ids: list[UUID]) -> list[FilmWork]:
        """Fetch full data by film_work ids."""

        if not film_work_ids:
            return []

        with closing(
            psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row)
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    FILM_WORK_DETAILS, {"film_work_ids": film_work_ids}
                )
                film_rows = list(cursor.fetchall())

                cursor.execute(
                    FILM_WORK_GENRES, {"film_work_ids": film_work_ids}
                )
                genre_rows = list(cursor.fetchall())

                cursor.execute(
                    FILM_WORK_PERSONS, {"film_work_ids": film_work_ids}
                )
                person_rows = list(cursor.fetchall())

        genres_by_film = group_genres_by_film(genre_rows)
        persons_by_film = group_persons_by_film(person_rows)
        result = [
            build_film_work(
                row,
                genres_by_film.get(row["id"], []),
                persons_by_film.get(
                    row["id"],
                    {"directors": [], "actors": [], "writers": []},
                ),
            )
            for row in film_rows
        ]
        return result

    @backoff()
    def fetch_genres(
        self,
        genre_ids: list[UUID],
    ) -> list[Genre]:
        """Fetch genres by ids."""

        if not genre_ids:
            return []

        with closing(
            psycopg.connect(
                self.settings.postgres_dsn,
                row_factory=dict_row,
            )
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    GENRE_DETAILS,
                    {"genre_ids": genre_ids},
                )

                rows = cursor.fetchall()

        return [build_genre(row) for row in rows]

    @backoff()
    def fetch_persons(
        self,
        person_ids: list[UUID],
    ) -> list[dict]:
        """Fetch persons data by ids from Postgres."""
        if not person_ids:
            return []

        with closing(
            psycopg.connect(
                self.settings.postgres_dsn,
                row_factory=dict_row,
            )
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    PERSON_DETAILS,
                    {"person_ids": person_ids},
                )
                rows = cursor.fetchall()

        return list(rows)

    def extract_persons(
        self,
        checkpoint_state: CheckpointState,
    ) -> tuple[list[Person], CheckpointState]:
        """Extract changed persons."""
        rows = self.fetch_changed_entities(
            ENTITY_TYPE_PERSON,
            checkpoint_state,
        )

        if not rows:
            return [], checkpoint_state

        person_ids = [row["id"] for row in rows]

        raw_person_rows = self.fetch_persons(person_ids)

        persons = build_persons_from_rows(raw_person_rows)

        checkpoint = build_checkpoint_state(rows[-1])
        logger.info("Fetched %s persons from PostgreSQL", len(persons))

        return persons, checkpoint

    def extract_film_works(
        self, entity_type: EntityType, checkpoint_state: CheckpointState
    ) -> tuple[list[FilmWork], CheckpointState]:
        """Run the full data extraction cycle for one entity type."""

        rows = self.fetch_changed_entities(entity_type, checkpoint_state)
        if not rows:
            return [], checkpoint_state

        entity_ids = [row["id"] for row in rows]
        film_work_ids = self.fetch_film_work_ids(entity_type, entity_ids)
        film_works = self.fetch_film_works(film_work_ids)
        checkpoint = build_checkpoint_state(rows[-1])
        logger.info(
            "Fetched %s film works from PostgreSQL for entity type %s",
            len(film_works),
            entity_type,
        )
        result = (film_works, checkpoint)
        return result

    def extract_genres(
        self,
        checkpoint_state: CheckpointState,
    ) -> tuple[list[Genre], CheckpointState]:
        """Extract changed genres."""

        rows = self.fetch_changed_entities(
            ENTITY_TYPE_GENRE,
            checkpoint_state,
        )

        if not rows:
            return [], checkpoint_state

        genre_ids = [row["id"] for row in rows]
        genres = self.fetch_genres(genre_ids)
        checkpoint = build_checkpoint_state(rows[-1])
        logger.info(
            "Fetched %s genres from PostgreSQL",
            len(genres),
        )

        return genres, checkpoint


def iter_batches(
    items: list[FilmWork], batch_size: int
) -> Iterator[list[FilmWork]]:
    """Split items into fixed-size batches."""

    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def normalize_checkpoint(value: datetime | str) -> str:
    """Convert a checkpoint value to string."""

    if isinstance(value, datetime):
        result = value.isoformat()
        return result
    result = value
    return result


def build_checkpoint_state(row: RowData) -> CheckpointState:
    """Build a checkpoint state from the last processed row."""

    result = {
        "modified": normalize_checkpoint(row["modified"]),
        "id": str(row["id"]),
    }
    return result


def get_changed_entities_query(entity_type: EntityType) -> str:
    """Return SQL query for reading changed entities."""

    table_map = {
        ENTITY_TYPE_FILM_WORK: "film_work",
        ENTITY_TYPE_GENRE: "genre",
        ENTITY_TYPE_PERSON: "person",
    }
    result = query_changed_entities(table_map[entity_type])
    return result


def get_film_work_ids_query(entity_type: EntityType) -> str:
    """Return SQL query for finding related film works by entity."""

    query_map = {
        ENTITY_TYPE_FILM_WORK: FILM_WORK_IDS_BY_SELF,
        ENTITY_TYPE_GENRE: FILM_WORK_IDS_BY_GENRE,
        ENTITY_TYPE_PERSON: FILM_WORK_IDS_BY_PERSON,
    }
    result = query_map[entity_type]
    return result
