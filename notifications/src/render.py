"""Рендер шаблона уведомления. Должно рендериться так же, как
реально отправит воркер, чтобы точно видеть что уйдет пользователю.

Используется SandboxedEnvironment, так как шаблон могут писать админы вручную."""

from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


def render(text: str | None, payload: dict[str, Any]) -> str | None:
    """Подставить payload в {{ var }} - плейсхолдеры text."""
    if text is None:
        return None
    return _env.from_string(text).render(**payload)
