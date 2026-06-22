"""App logging."""

import logging


def configure_logging(level: str) -> None:
    """Apply the global logging config for ETL process."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
