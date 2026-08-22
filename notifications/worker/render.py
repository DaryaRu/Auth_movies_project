"""Рендер шаблона уведомления."""

from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

# StrictUndefined: плейсхолдер без значения в payload бросает исключение.
# Опечатка в шаблоне/payload попадает в notifications.error_message.
# Используется SandboxedEnvironment, так как шаблон могут писать админы вручную.
_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


def render(text: str | None, payload: dict[str, Any]) -> str | None:
    """Подставить payload в {{ var }}-плейсхолдеры text."""
    if text is None:
        return None
    return _env.from_string(text).render(**payload)
