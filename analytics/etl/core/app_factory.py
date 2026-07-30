import logging

from core.lifespans import lifespan
from extractors import broker
from faststream import FastStream


def create_app() -> FastStream:
    logging.basicConfig(level=logging.INFO)
    return FastStream(
    broker,
    lifespan=lifespan,
)
