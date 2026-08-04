import sentry_sdk

from src.core.config import settings


def sentry_init() -> None:
    """Инициализирует Sentry, если задан SENTRY_DSN."""
    if not settings.SENTRY_DSN:
        return
    # Только ошибки, трейсы собирает Jaeger.
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0,
    )
