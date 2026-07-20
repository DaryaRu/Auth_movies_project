import logging

from faststream import FastStream

from core.lifespans import lifespan
from extractors import broker


def create_app() -> FastStream:
    logging.basicConfig(level=logging.INFO)
    return FastStream(
    broker,
    lifespan=lifespan,
)
