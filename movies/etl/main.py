"""Run the ETL application."""

from config import Settings
from extract.postgres_extractor import PostgresExtractor
from load.elastic import ElasticsearchWriter
from logging_config import configure_logging
from pipeline.orchestrator import EtlOrchestrator
from state.json_storage import JsonFileStorage
from state.state import State


def main() -> None:
    """Configure dependencies and run ETL process."""
    settings = Settings()
    configure_logging(settings.log_level)

    state_storage = JsonFileStorage(settings.state_file)
    state = State(state_storage)

    extractor = PostgresExtractor(settings)
    writer = ElasticsearchWriter(settings)

    for index_name, schema in settings.elastic_map.items():
        writer.check_or_create_index(index_name, schema)

    orchestrator = EtlOrchestrator(settings, state, extractor, writer)
    orchestrator.run_forever()


if __name__ == "__main__":
    main()
