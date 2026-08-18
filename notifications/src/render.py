"""Рендер шаблона уведомления. Должно рендериться так же, как
реально отправит воркер, чтобы точно видеть что уйдет пользователю."""

from typing import Any

from jinja2 import Environment, StrictUndefined

_env = Environment(undefined=StrictUndefined, autoescape=False)


def render(text: str | None, payload: dict[str, Any]) -> str | None:
    """Подставить payload в {{ var }} - плейсхолдеры text."""
    if text is None:
        return None
    return _env.from_string(text).render(**payload)
