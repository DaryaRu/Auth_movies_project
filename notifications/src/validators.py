"""Валидация содержимого шаблона перед сохранением (POST/PATCH /templates/)."""

from typing import Any

from jinja2 import meta, nodes
from jinja2.exceptions import TemplateError, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment, SecurityError

from src.render import render

_env = SandboxedEnvironment()


class TemplateValidationError(Exception):
    """Ошибка, когда шаблон не проходит валидацию."""


def _base_variable_name(node: nodes.Node) -> str | None:
    """Базовая переменная цепочки .attr/[key]-обращений (None, если основание — не переменная)."""
    while isinstance(node, (nodes.Getattr, nodes.Getitem)):
        node = node.node
    return node.name if isinstance(node, nodes.Name) else None


def _check_no_nested_access(ast: nodes.Template, label: str) -> None:
    """Запрещает {{ var.attr }} и {{ var[key] }} — разрешены только плоские {{ var }}."""
    for node in ast.find_all((nodes.Getattr, nodes.Getitem)):
        var_name = _base_variable_name(node) or "?"
        raise TemplateValidationError(
            f"Nested access to '{var_name}' is not supported in {label}: "
            f"only flat variables are allowed, not '{var_name}.attr' or '{var_name}[key]'"
        )


def _used_variables(text: str, label: str) -> set[str]:
    """Переменные, используемые в Jinja2-шаблоне."""
    ast = _env.parse(text)
    _check_no_nested_access(ast, label)
    return meta.find_undeclared_variables(ast)


def validate_template_content(
    subject: str | None, body: str, allowed_variables: list[str]
) -> None:
    """Проверки:
    1. Синтаксис Jinja2 валиден (TemplateSyntaxError при парсинге).
    2. Используемые переменные — подмножество allowed_variables.
    3. Шаблон реально рендерится: заглушки по allowed_variables прогоняются через SandboxedEnvironment.
    """
    used_variables: set[str] = set()
    for label, text in (("body", body), ("subject", subject or "")):
        try:
            used_variables |= _used_variables(text, label)
        except TemplateSyntaxError as e:
            raise TemplateValidationError(
                f"Invalid syntax in {label}: {e}"
            ) from e

    unknown = used_variables - set(allowed_variables)
    if unknown:
        raise TemplateValidationError(
            f"Template uses variables not in allowed_variables: {sorted(unknown)}"
        )

    placeholder_payload: dict[str, Any] = {
        var: f"<{var}>" for var in allowed_variables
    }
    try:
        render(body, placeholder_payload)
        render(subject, placeholder_payload)
    except SecurityError as e:
        raise TemplateValidationError(
            f"Template uses a construct not allowed for managers: {e}"
        ) from e
    except UndefinedError as e:
        raise TemplateValidationError(
            f"Template render failed — missing variable: {e}"
        ) from e
    except TemplateError as e:
        raise TemplateValidationError(f"Template render failed: {e}") from e
    except (TypeError, ZeroDivisionError) as e:
        raise TemplateValidationError(
            f"Template render failed — invalid operation for placeholder value: {e}"
        ) from e
