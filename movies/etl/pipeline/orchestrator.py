"""Manage ETL pipeline execution."""

import logging
import time

from config import Settings
from extract.postgres_extractor import (
    DEFAULT_ID_VALUE,
    DEFAULT_MODIFIED_VALUE,
    ENTITY_TYPE_FILM_WORK,
    ENTITY_TYPE_GENRE,
    ENTITY_TYPE_PERSON,
    CheckpointState,
    PostgresExtractor,
    iter_batches,
)
from load.elastic import ElasticsearchWriter
from state.state import State

logger = logging.getLogger(__name__)

FILM_WORK_STATE_KEYS = {
    ENTITY_TYPE_FILM_WORK: "film_work_etl:film_work_modified",
    ENTITY_TYPE_GENRE: "film_work_etl:genre_modified",
    ENTITY_TYPE_PERSON: "film_work_etl:person_modified",
}

GENRE_STATE_KEY = "genre_etl:genre_modified"
PERSON_STATE_KEY = "person_etl:person_modified"


class EtlOrchestrator:
    """Manage ETL pipeline stages."""

    def __init__(
        self,
        settings: Settings,
        state: State,
        extractor: PostgresExtractor,
        writer: ElasticsearchWriter,
    ) -> None:
        """Initialize with settings, state, extractor, and writer."""
        self.settings = settings
        self.state = state
        self.extractor = extractor
        self.writer = writer

    def run_forever(self) -> None:
        """Run ETL continuously with pauses between cycles."""
        while True:
            self.run_once()
            time.sleep(self.settings.etl_poll_interval)

    def _run_pipeline(
        self,
        *,
        extract_func,
        state_key: str,
        index: str,
        entity_name: str,
    ) -> None:
        """Run one cycle for a entity type and index."""
        checkpoint_state = get_checkpoint_state(
            self.state.get_state(state_key)
        )

        items, next_checkpoint = extract_func(checkpoint_state)

        if not items:
            logger.debug("No modified %s found", entity_name)
            return

        for batch in iter_batches(items, self.settings.etl_chunk_size):
            self.writer.bulk_save(index, batch)

        self.state.set_state(state_key, next_checkpoint)

        logger.info(
            "Checkpoint saved for %s: %s",
            entity_name,
            next_checkpoint,
        )

    def run_once(self) -> None:
        for entity_type, state_key in FILM_WORK_STATE_KEYS.items():
            self._run_pipeline(
                extract_func=lambda cp: self.extractor.extract_film_works(
                    entity_type,
                    cp,
                ),
                state_key=state_key,
                index=self.settings.elastic_movies_index,
                entity_name=entity_type,
            )
        self._run_pipeline(
            extract_func=self.extractor.extract_genres,
            state_key=GENRE_STATE_KEY,
            index=self.settings.elastic_genres_index,
            entity_name="genre",
        )

        self._run_pipeline(
            extract_func=self.extractor.extract_persons,
            state_key=PERSON_STATE_KEY,
            index=self.settings.elastic_persons_index,
            entity_name="person",
        )


def get_checkpoint_state(
    stored_state: CheckpointState | None,
) -> CheckpointState:
    """Normalize state to a checkpoint with modified and id."""

    if stored_state is None:
        result = {
            "modified": DEFAULT_MODIFIED_VALUE,
            "id": DEFAULT_ID_VALUE,
        }
        return result

    result = {
        "modified": stored_state["modified"],
        "id": stored_state["id"],
    }
    return result
