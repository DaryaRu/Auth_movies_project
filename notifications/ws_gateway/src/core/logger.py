"""Логирование приложения."""

import logging
import re

_TOKEN_RE = re.compile(r"(token=)[A-Za-z0-9\-_\.]+")


class TokenRedactionFilter:
    """Фильтр, маскирующий JWT-токены в логах."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _TOKEN_RE.sub(r"\1***", record.msg)
        if record.args:
            record.args = tuple(
                _TOKEN_RE.sub(r"\1***", a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "token_redaction": {
            "()": "src.core.logger.TokenRedactionFilter",
        },
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
            "filters": ["token_redaction"],
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "ws_gateway": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
