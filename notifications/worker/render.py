"""Рендер шаблона уведомления."""

from typing import Any

from jinja2 import Environment, StrictUndefined

# StrictUndefined: плейсхолдер без значения в payload бросает исключение.
# Опечатка в шаблоне/payload попадает в notifications.error_message.
_env = Environment(undefined=StrictUndefined, autoescape=False)


def render(text: str | None, payload: dict[str, Any]) -> str | None:
    """Подставить payload в {{ var }}-плейсхолдеры text."""
    if text is None:
        return None
    return _env.from_string(text).render(**payload)
