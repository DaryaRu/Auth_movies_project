import sentry_sdk
from core import config


def sentry_init() -> None:
    """Инициализирует Sentry, если задан SENTRY_DSN."""
    if not config.SENTRY_DSN:
        return
    # Только ошибки, трейсы собирает Jaeger.
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.ENVIRONMENT,
        traces_sample_rate=0,
    )
