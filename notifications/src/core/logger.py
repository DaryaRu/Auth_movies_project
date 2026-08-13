"""Логирование приложения."""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
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
            # Без явного stream StreamHandler пишет в stderr по умолчанию —
            # GELF тогда помечает обычные INFO-логи как ошибки.
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "notifications": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
