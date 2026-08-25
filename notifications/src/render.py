"""Рендер шаблона уведомления. Должно рендериться так же, как
реально отправит воркер, чтобы точно видеть что уйдет пользователю.

Используется SandboxedEnvironment, так как шаблон могут писать админы вручную."""

import html
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


def render(
    text: str | None, payload: dict[str, Any], *, escape_html: bool = False
) -> str | None:
    """Подставить payload в {{ var }} - плейсхолдеры text.

    Для push: escape_html=True экранирует строковые значения payload перед подстановкой.
    """
    if text is None:
        return None
    if escape_html:
        payload = {
            key: html.escape(value) if isinstance(value, str) else value
            for key, value in payload.items()
        }
    return _env.from_string(text).render(**payload)
