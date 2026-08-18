import logging
import sys

from consumer import broker
from core.lifespans import lifespan
from faststream import FastStream

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

app = FastStream(broker, lifespan=lifespan)
